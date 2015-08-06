# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon, Pierre Mazière
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import re
import base64
from decimal import Decimal
import math
import random
from cStringIO import StringIO
from urllib import urlencode


from weboob.capabilities.bank import Account, Investment
from weboob.browser.elements import method, ListElement, ItemElement, SkipItem
from weboob.exceptions import ParseError
from weboob.browser.pages import LoggedPage, HTMLPage, FormNotFound, pagination
from weboob.browser.filters.html import Attr
from weboob.browser.filters.standard import CleanText, Field, Regexp, Format, \
                                            CleanDecimal, Map, AsyncLoad, Async
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=Decimal(0))
    return CleanDecimal(*args, **kwargs)


class LCLBasePage(HTMLPage):
    def get_from_js(self, pattern, end, is_list=False):
        """
        find a pattern in any javascript text
        """
        value = None
        for script in self.doc.xpath('//script'):
            txt = script.text
            if txt is None:
                continue

            start = txt.find(pattern)
            if start < 0:
                continue

            while True:
                if value is None:
                    value = ''
                else:
                    value += ','
                value += txt[start+len(pattern):start+txt[start+len(pattern):].find(end)+len(pattern)]

                if not is_list:
                    break

                txt = txt[start+len(pattern)+txt[start+len(pattern):].find(end):]

                start = txt.find(pattern)
                if start < 0:
                    break
            return value


class LCLVirtKeyboard(MappedVirtKeyboard):
    symbols={'0': '9da2724133f2221482013151735f033c',
             '1': '873ab0087447610841ae1332221be37b',
             '2': '93ce6c330393ff5980949d7b6c800f77',
             '3': 'b2d70c69693784e1bf1f0973d81223c0',
             '4': '498c8f5d885611938f94f1c746c32978',
             '5': '359bcd60a9b8565917a7bf34522052c3',
             '6': 'aba912172f21f78cd6da437cfc4cdbd0',
             '7': 'f710190d6b947869879ec02d8e851dfa',
             '8': 'b42cc25e1539a15f767aa7a641f3bfec',
             '9': 'cc60e5894a9d8e12ee0c2c104c1d5490'
            }

    url="/outil/UAUT/Clavier/creationClavier?random="

    color=(255,255,255,255)

    def __init__(self, basepage):
        img=basepage.doc.find("//img[@id='idImageClavier']")
        random.seed()
        self.url += "%s"%str(long(math.floor(long(random.random()*1000000000000000000000))))
        super(LCLVirtKeyboard, self).__init__(StringIO(basepage.browser.open(self.url).content), basepage.doc,img,self.color, "id")
        self.check_symbols(self.symbols,basepage.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code=MappedVirtKeyboard.get_symbol_code(self, md5sum)
        return code[-2:]

    def get_string_code(self, string):
        code=''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(HTMLPage):
    def on_load(self):
        try:
            form = self.get_form(xpath='//form[@id="setInfosCGS" or @name="form"]')
        except FormNotFound:
            return

        form.submit()

    def myXOR(self,value,seed):
        s = ''
        for i in xrange(len(value)):
            s += chr(seed^ord(value[i]))
        return s

    def login(self, login, passwd):
        try:
            vk = LCLVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.exception(err)
            return False

        password = vk.get_string_code(passwd)

        seed = -1
        s = "var aleatoire = "
        for script in self.doc.findall("//script"):
            if script.text is None or len(script.text) == 0:
                continue
            offset = script.text.find(s)
            if offset != -1:
                seed = int(script.text[offset+len(s)+1:offset+len(s)+2])
                break
        if seed==-1:
            raise ParseError("Variable 'aleatoire' not found")

        form = self.get_form('//form[@id="formAuthenticate"]')
        form['identifiant'] = login
        form['postClavierXor'] = base64.b64encode(self.myXOR(password,seed))
        try:
            form['identifiantRouting'] = self.browser.IDENTIFIANT_ROUTING
        except AttributeError:
            pass

        try:
            form.submit()
        except BrowserUnavailable:
            # Login is not valid
            return False
        return True

    def is_error(self):
        errors = self.doc.xpath(u'//*[@class="erreur" or @class="messError"]')
        return len(errors) > 0


class ContractsPage(LoginPage):
    def on_load(self):
        if self.is_error():
            raise BrowserIncorrectPassword()
        self.select_contract()

    def select_contract(self):
        # XXX We select automatically the default contract in list. We should let user
        # ask what contract he wants to see, or display accounts for all contracts.
        link = self.doc.xpath('//a[contains(text(), "Votre situation globale")]')
        if len(link):
            self.browser.location(link[0].attrib['href'])
        else:
            form = self.get_form(nr=0)
            form.submit()

class AccountsPage(LoggedPage, HTMLPage):
    def on_load(self):
        warn = self.doc.xpath('//div[@id="attTxt"]')
        if len(warn) > 0:
            raise BrowserIncorrectPassword(warn[0].text)

    @method
    class get_list(ListElement):
        item_xpath = '//tr[contains(@onclick, "redirect")]'
        flush_at_end = True

        class account(ItemElement):
            klass = Account

            def condition(self):
                return '/outil/UWLM/ListeMouvement' in self.el.attrib['onclick']

            NATURE2TYPE = {'006': Account.TYPE_CHECKING,
                           '046': Account.TYPE_SAVINGS,
                           '049': Account.TYPE_SAVINGS,
                           '068': Account.TYPE_MARKET,
                           '069': Account.TYPE_SAVINGS,
                          }

            obj__link_id = Format('%s&mode=55', Regexp(CleanText('./@onclick'), "'(.*)'"))
            obj_id = Regexp(Field('_link_id'), r'.*agence=(\w+).*compte=(\w+)', r'\1\2')
            obj__coming_links = []
            obj_label = CleanText('.//div[@class="libelleCompte"]')
            obj_balance = CleanDecimal('.//td[has-class("right")]', replace_dots=True)
            obj_currency = FrenchTransaction.Currency('.//td[has-class("right")]')
            obj_type = Map(Regexp(Field('_link_id'), r'.*nature=(\w+)'), NATURE2TYPE, default=Account.TYPE_UNKNOWN)
            obj__market_link = None

        class card(ItemElement):
            def condition(self):
                return '/outil/UWCB/UWCBEncours' in self.el.attrib['onclick']

            def parse(self, el):
                link = Regexp(CleanText('./@onclick'), "'(.*)'")(el)
                id = Regexp(CleanText('./@onclick'), r'.*AGENCE=(\w+).*COMPTE=(\w+).*CLE=(\w+)', r'\1\2\3')(el)

                account = self.parent.objects[id]
                if not account.coming:
                    account.coming = Decimal('0')

                account.coming += CleanDecimal('.//td[has-class("right")]', replace_dots=True)(el)
                account._coming_links.append(link)
                raise SkipItem()

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(?P<category>CB) (?P<text>RETRAIT) DU (?P<dd>\d+)/(?P<mm>\d+)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>(PRLV|PE)( SEPA)?) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>CHQ\.) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CHECK),
                (re.compile('^(?P<category>RELEVE CB) AU (\d+)/(\d+)/(\d+)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>CB) (?P<text>.*) (?P<dd>\d+)/(?P<mm>\d+)/(?P<yy>\d+)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>(ECHEANCE\s*)?PRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<category>(EVI|VIR(EM(EN)?)?T?)(.PERMANENT)? ((RECU|FAVEUR) TIERS|SEPA RECU)?)( /FRM)?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COM(MISSIONS?)?)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>ABON.*?)\s*.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>RESULTAT .*?)\s*.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>TRAIT\..*?)\s*.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REM CHQ) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]
class Pagination(object):
    def next_page(self):
        links = self.page.doc.xpath('//div[@class="pagination"] /a')
        if len(links) == 0:
            return
        for link in links:
            if link.xpath('./span')[0].text == 'Page suivante':
                return link.attrib.get('href')
        return

class AccountHistoryPage(LoggedPage, HTMLPage):
    class _get_operations(Pagination, Transaction.TransactionsElement):
        item_xpath = '//table[has-class("tagTab") and (not(@style) or @style="")]/tr'
        head_xpath = '//table[has-class("tagTab") and (not(@style) or @style="")]/tr/th'

        col_raw = [u'Vos opérations', u'Libellé']

        class item(Transaction.TransactionElement):
            load_details = Attr('.', 'href', default=None) & AsyncLoad
            def condition(self):
                return self.parent.get_colnum('date') is not None and \
                       len(self.el.findall('td')) >= 3 and \
                       self.el.get('class') and \
                       'tableTr' not in self.el.get('class')

            def validate(self, obj):
                if obj.category == 'RELEVE CB':
                    return

                raw = Async('details', CleanText(u'//td[contains(text(), "Libellé")]/following-sibling::*[1]', default=obj.raw))(self)
                if raw:
                    obj.raw = raw
                return True

    @pagination
    def get_operations(self):
        return self._get_operations(self)()


class CBHistoryPage(AccountHistoryPage):
    def get_operations(self):
        for tr in self._get_operations(self)():
            tr.type = tr.TYPE_CARD
            yield tr


class CBListPage(CBHistoryPage):
    def get_cards(self):
        cards = []
        for tr in self.doc.getiterator('tr'):
            link = Regexp(CleanText('./@onclick'), "'(.*)'", default=None)(tr)
            if link is not None and link.startswith('/outil/UWCB/UWCBEncours') and 'listeOperations' in link:
                cards.append(link)
        return cards


class BoursePage(LoggedPage, HTMLPage):
    def get_next(self):
        return re.search('"(.*?)"', self.doc.xpath('.//body')[0].attrib['onload']).group(1)

    def populate(self, accounts):
        for a in accounts:
            for tr in self.doc.xpath('.//table[contains(@class, "tableau_comptes_details")]/tbody/tr'):
                ac_code = tr.xpath('.//td[2]/div')[-1].text.strip().split(' - ')
                if a.id == '%s%s' % (ac_code[0], ac_code[1]):
                    a._market_link = Regexp(CleanText('.//td[2]/@onclick'), "'(.*?)'")(tr)
                    a.balance += CleanDecimal('.//td[has-class("last")]', replace_dots=True)(tr)
            yield a

    @method
    class iter_investment(ListElement):
        item_xpath = '//table[@id="tableValeurs"]/tbody/tr[not(@class) and count(descendant::td) > 1]'
        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//td[2]/div/a')
            obj_code = CleanText('.//td[2]/div/br/following-sibling::text()')
            obj_quantity = MyDecimal('.//td[3]/span')
            obj_diff = MyDecimal('.//td[7]/span')
            obj_valuation = MyDecimal('.//td[5]')

            def obj_unitvalue(self):
                if "%" in CleanText('.//td[4]')(self) and "%" in CleanText('.//td[6]')(self):
                    return self.obj_valuation(self) / self.obj_quantity(self)
                else:
                    return MyDecimal('.//td[4]')(self)

            def obj_unitprice(self):
                if "%" in CleanText('.//td[4]')(self) and "%" in CleanText('.//td[6]')(self):
                    return self.obj_valuation(self) / self.obj_quantity(self)
                    return (self.obj_valuation(self) - self.obj_diff(self)) / self.obj_quantity(self)
                else:
                    return MyDecimal('.//td[6]')(self)

class DiscPage(LoggedPage, HTMLPage):
    def come_back(self):
        form = self.get_form()
        form.submit()

class NoBoursePage(LoggedPage, HTMLPage):
    pass

class AVPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '//table[@class]/tbody/tr'

        class account(ItemElement):
            klass = Account

            obj__owner = CleanText('.//td[1]') & Regexp(pattern=r' ([^ ]+)$')
            obj_label = Format(u'%s %s', CleanText('.//td/a'), obj__owner)
            obj_balance = CleanDecimal('.//td[has-class("right")]', replace_dots=True)
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj__link_id = None
            obj__market_link = None
            obj__coming_links = []

            def obj_id(self):
                _id = CleanText('.//td/a/@id')(self)
                if not _id:
                    _id = Regexp(CleanText('.//td/a/@href'), r'ID_CONTRAT=(\d+)')(self)
                return Format(u'%s%s', CleanText(Field('label'), replace=[(' ', '')]), _id)(self)

            def obj__form(self):
                form_id = Attr('.//td/a', 'id', default=None)(self)
                if not form_id:
                    return
                form = self.page.get_form('//form[@id="formRoutage"]')
                form['ID_CONTRAT'] = re.search(r'^(.*?)-', form_id).group(1)
                form['PRODUCTEUR'] = re.search(r'-(.*?)$', form_id).group(1)
                return form


class AVDetailPage(LoggedPage, LCLBasePage):
    def sub(self):
        form = self.get_form(name="formulaire")
        cName = self.get_from_js('.cName.value  = "', '";')
        if cName:
            form['cName'] = cName
            form['cValue'] = self.get_from_js('.cValue.value  = "', '";')
            form['cMaxAge'] = '-1'
        form.submit()

    def come_back(self):
        session = self.get_from_js('idSessionSag = "', '"')
        params = {}
        params['sessionSAG'] = session
        params['stbpg'] = 'pagePU'
        params['act'] = ''
        params['typeaction'] = 'reroutage_retour'
        params['site'] = 'LCLI'
        params['stbzn'] = 'bnc'
        self.browser.location('https://assurance-vie-et-prevoyance.secure.lcl.fr/filiale/entreeBam?%s' % urlencode(params))

    @method
    class iter_investment(ListElement):
        item_xpath = '(//table[@class="table"])[1]/tbody/tr'
        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//td[1]/a | .//td[1]/span ')
            obj_code = CleanText('.//td[1]/a/@id')
            obj_quantity = MyDecimal('.//td[4]/span')
            obj_unitvalue = MyDecimal('.//td[2]/span')
            obj_valuation = MyDecimal('.//td[5]/span')

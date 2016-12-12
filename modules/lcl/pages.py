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

import json
import re, requests, base64, math, random
from decimal import Decimal
from cStringIO import StringIO
from urllib import urlencode
from datetime import datetime, timedelta, date

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment, Recipient, TransferError, Transfer
from weboob.browser.elements import method, ListElement, TableElement, ItemElement, SkipItem
from weboob.exceptions import ParseError
from weboob.browser.pages import LoggedPage, HTMLPage, FormNotFound, pagination
from weboob.browser.filters.html import Attr, Link
from weboob.browser.filters.standard import CleanText, Field, Regexp, Format, Date, \
                                            CleanDecimal, Map, AsyncLoad, Async, Env, \
                                            TableCell, Eval
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=Decimal(0))
    return CleanDecimal(*args, **kwargs)

def myXOR(value,seed):
    s = ''
    for i in xrange(len(value)):
        s += chr(seed^ord(value[i]))
    return s


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
        form['postClavierXor'] = base64.b64encode(myXOR(password,seed))
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
        return len(errors) > 0 and not self.doc.xpath('//a[@href="/outil/UWHO/Accueil/"]')


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

        # XXX Ugly Hack to replace account by second occurrence.
        # LCL pro website sometimes display the same account twice and only second link is valid to fetch transactions.
        def store(self, obj):
            assert obj.id
            if obj.id in self.objects:
                self.logger.warning('There are two objects with the same ID! %s' % obj.id)
            self.objects[obj.id] = obj
            return obj

        item_xpath = '//tr[contains(@onclick, "redirect")]'
        flush_at_end = True

        class account(ItemElement):
            klass = Account

            def condition(self):
                return '/outil/UWLM/ListeMouvement' in self.el.attrib['onclick']

            NATURE2TYPE = {'001': Account.TYPE_SAVINGS,
                           '005': Account.TYPE_CHECKING,
                           '006': Account.TYPE_CHECKING,
                           '007': Account.TYPE_SAVINGS,
                           '012': Account.TYPE_SAVINGS,
                           '023': Account.TYPE_CHECKING,
                           '046': Account.TYPE_SAVINGS,
                           '047': Account.TYPE_SAVINGS,
                           '049': Account.TYPE_SAVINGS,
                           '068': Account.TYPE_MARKET,
                           '069': Account.TYPE_SAVINGS,
                          }

            obj__link_id = Format('%s&mode=190', Regexp(CleanText('./@onclick'), "'(.*)'"))
            obj__agence = Regexp(Field('_link_id'), r'.*agence=(\w+)')
            obj__compte = Regexp(Field('_link_id'), r'compte=(\w+)')
            obj_id = Format('%s%s', Field('_agence'), Field('_compte'))
            obj__transfer_id = Format('%s0000%s', Field('_agence'), Field('_compte'))
            obj__coming_links = []
            obj_label = CleanText('.//div[@class="libelleCompte"]')
            obj_balance = MyDecimal('.//td[has-class("right")]', replace_dots=True)
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


class LoansPage(LoggedPage, HTMLPage):
    @method
    class get_list(TableElement):
        item_xpath = '//table[.//th[contains(text(), "Emprunteur")]]/tbody/tr[td[3]]'
        head_xpath = '//table[.//th[contains(text(), "Emprunteur")]]/thead/tr/th'
        flush_at_end = True

        col_id = re.compile('Emprunteur')
        col_balance = [u'Capital restant dû', re.compile('Sommes totales restant dues'), re.compile('Montant disponible')]

        class account(ItemElement):
            klass = Account

            obj_balance = CleanDecimal(TableCell('balance'), replace_dots=True, sign=lambda x: -1)
            obj_currency = FrenchTransaction.Currency(TableCell('balance'))
            obj_type = Account.TYPE_LOAN
            obj_id = Env('id')

            def obj_label(self):
                has_type = CleanText('./ancestor::table[.//th[contains(text(), "Type")]]', default=None)(self)
                return CleanText('./td[2]')(self) if has_type else CleanText('./ancestor::table/preceding-sibling::div[1]')(self).split(' - ')[0]

            def parse(self, el):
                label = Field('label')(self)
                trs = self.xpath('//td[contains(text(), "%s")]/ancestor::tr[1] | ./ancestor::table[1]/tbody/tr' % label)
                i = [i for i in range(len(trs)) if el == trs[i]]
                i = i[0] if i else 0
                label = label.replace(' ', '')
                self.env['id'] = "%s%s%s" % (Regexp(CleanText(TableCell('id')), r'(\w+)\s-\s(\w+)', r'\1\2')(self), label.replace(' ', ''), i)


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
            (re.compile('^VIREMENT.*'),FrenchTransaction.TYPE_TRANSFER),
            (re.compile('.*(PRELEVEMENTS|PRELVT|TIP).*'),FrenchTransaction.TYPE_ORDER),
            (re.compile('.*CHEQUE.*'), FrenchTransaction.TYPE_CHECK),
            (re.compile('.*ESPECES.*'), FrenchTransaction.TYPE_DEPOSIT),
            (re.compile('.*(CARTE|CB).*'), FrenchTransaction.TYPE_CARD),
            (re.compile('.*(AGIOS|ANNULATIONS|IMPAYES|CREDIT).*'), FrenchTransaction.TYPE_BANK),
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

            def obj_type(self):
                type = Async('details', CleanText(u'//td[contains(text(), "Nature de l\'opération")]/following-sibling::*[1]'))(self)
                if not type:
                    return Transaction.TYPE_UNKNOWN
                for pattern, _type in Transaction.PATTERNS:
                    match = pattern.match(type)
                    if match:
                        return _type
                        break
                return Transaction.TYPE_UNKNOWN

            def condition(self):
                return self.parent.get_colnum('date') is not None and \
                       len(self.el.findall('td')) >= 3 and \
                       self.el.get('class') and \
                       'tableTr' not in self.el.get('class')

            def validate(self, obj):
                if obj.category == 'RELEVE CB':
                    obj.type = Transaction.TYPE_CARD_SUMMARY
                    obj.deleted = True

                raw = Async('details', CleanText(u'//td[contains(text(), "Libellé")]/following-sibling::*[1]|//td[contains(text(), "Nom du donneur")]/following-sibling::*[1]', default=obj.raw))(self)
                if raw:
                    if obj.raw in raw or raw in obj.raw or ' ' not in obj.raw:
                        obj.raw = raw
                        obj.label = raw
                    else:
                        obj.label = '%s %s' % (obj.raw, raw)
                        obj.raw = '%s %s' % (obj.raw, raw)
                if not obj.date:
                    obj.date = Async('details', Date(CleanText(u'//td[contains(text(), "Date de l\'opération")]/following-sibling::*[1]', default=u''), default=NotAvailable))(self)
                    obj.rdate = obj.date
                    obj.vdate = Async('details', Date(CleanText(u'//td[contains(text(), "Date de valeur")]/following-sibling::*[1]', default=u''), default=NotAvailable))(self)
                    obj.amount = Async('details', CleanDecimal(u'//td[contains(text(), "Montant")]/following-sibling::*[1]', replace_dots=True, default=NotAvailable))(self)
                # ugly hack to fix broken html
                if not obj.amount:
                    obj.amount = Async('details', CleanDecimal(u'//td[contains(text(), "Montant")]/following-sibling::*[1]', replace_dots=True, default=NotAvailable))(self)
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
    ENCODING='latin-1'

    def get_next(self):
        return re.search('"(.*?)"', self.doc.xpath('.//body')[0].attrib['onload']).group(1)

    def get_fullhistory(self):
        form = self.get_form(id="historyFilter")
        form['cashFilter'] = "ALL"
        # We can't go above 2 years
        form['beginDayfilter'] = (datetime.strptime(form['endDayfilter'], '%d/%m/%Y') - timedelta(days=730)).strftime('%d/%m/%Y')
        form.submit()

    @method
    class get_list(TableElement):
        item_xpath = '//table[has-class("tableau_comptes_details")]//tr[td and not(parent::tfoot)]'
        head_xpath = '//table[has-class("tableau_comptes_details")]/thead/tr/th'

        col_label = u'Comptes'
        col_balance = re.compile('Valorisation')

        class item(ItemElement):
            klass = Account

            load_details = Field('_market_link') & AsyncLoad

            obj_type = Account.TYPE_MARKET
            obj_balance = CleanDecimal(TableCell('balance'), replace_dots=True)
            obj_valuation_diff = Async('details') &  CleanDecimal('//td[contains(text(), "value latente")]/ \
                                                                  following-sibling::td[1]', replace_dots=True)
            obj__market_link = Regexp(Attr(TableCell('label'), 'onclick'), "'(.*?)'")
            obj__link_id = Async('details') & Link(u'//a[text()="Historique"]')
            obj__transfer_id = None

            def obj_id(self):
                return "%sbourse" % "".join(CleanText().filter((TableCell('label')(self)[0]).xpath('./div[not(b)]')).split(' - '))

            def obj_label(self):
                return "%s Bourse" % CleanText().filter((TableCell('label')(self)[0]).xpath('./div[b]'))

    @method
    class iter_investment(ListElement):
        item_xpath = '//table[@id="tableValeurs"]/tbody/tr[not(@class) and count(descendant::td) > 1]'
        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//td[2]/div/a')
            obj_code= CleanText('.//td[2]/div/br/following-sibling::text()') & Regexp(pattern='^([^ ]+).*', default=NotAvailable)
            obj_quantity = MyDecimal('.//td[3]/span')
            obj_diff = MyDecimal('.//td[7]/span')
            obj_valuation = MyDecimal('.//td[5]')

            def obj_unitvalue(self):
                if "%" in CleanText('.//td[4]')(self) and "%" in CleanText('.//td[6]')(self):
                    return NotAvailable
                return MyDecimal('.//td[4]/text()')(self)

            def obj_unitprice(self):
                if "%" in CleanText('.//td[4]')(self) and "%" in CleanText('.//td[6]')(self):
                    return NotAvailable
                return MyDecimal('.//td[6]')(self)

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table[@id="historyTable" and thead]/tbody/tr'
        head_xpath = '//table[@id="historyTable" and thead]/thead/tr/th'

        col_date = 'Date'
        col_label = u'Opération'
        col_quantity = u'Qté'
        col_code = u'Libellé'
        col_amount = 'Montant'

        def next_page(self):
            form = self.page.get_form(id="historyFilter")
            form['PAGE'] = int(form['PAGE']) + 1
            return requests.Request("POST", form.url, data=dict(form)) \
                   if self.page.doc.xpath('//*[@data-page = "%s"]' % form['PAGE']) else None

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_type = Transaction.TYPE_BANK
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True)
            obj_investments = Env('investments')

            def obj_label(self):
                return TableCell('label')(self)[0].xpath('./text()')[0].strip()

            def parse(self, el):
                i = None
                if CleanText(TableCell('code'))(self):
                    i = Investment()
                    i.label = Field('label')(self)
                    i.code = unicode(TableCell('code')(self)[0].xpath('./text()[last()]')[0]).strip()
                    i.quantity = MyDecimal(TableCell('quantity'))(self)
                    i.valuation = Field('amount')(self)
                    i.vdate = Field('date')(self)
                self.env['investments'] = [i] if i else []


class DiscPage(LoggedPage, HTMLPage):
    def come_back(self):
        form = self.get_form()
        form.submit()


class NoPermissionPage(LoggedPage, HTMLPage):
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
            obj__transfer_id = None

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
        return form.submit()

    def come_back(self):
        session = self.get_from_js('idSessionSag = "', '"')
        params = {}
        params['sessionSAG'] = session
        params['stbpg'] = 'pagePU'
        params['act'] = ''
        params['typeaction'] = 'reroutage_retour'
        params['site'] = 'LCLI'
        params['stbzn'] = 'bnc'
        return self.browser.location('https://assurance-vie-et-prevoyance.secure.lcl.fr/filiale/entreeBam?%s' % urlencode(params))

    def get_details(self, account, act=None):
        form = self.get_form(id="frm_fwk")
        form.submit()
        if act is not None:
            self.browser.location("entreeBam?sessionSAG=%s&act=%s" % (form['sessionSAG'], act))

    @method
    class iter_investment(ListElement):
        item_xpath = '//table[@class="table"]/tbody/tr[td[6]]'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//td[1]/a | .//td[1]/span ')
            obj_code = CleanText('.//td[1]/a/@id') & Regexp(pattern='^([^ ]+).*', default=NotAvailable)
            obj_quantity = MyDecimal('.//td[4]/span')
            obj_unitvalue = MyDecimal('.//td[2]/span')
            obj_valuation = MyDecimal('.//td[5]/span')
            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal('.//td[6]/span', replace_dots=True))

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table[@class="table"]/tbody/tr'
        head_xpath = '//table[@class="table"]/thead/tr/th'

        col_date = 'Date d\'effet'
        col_label = u'Opération(s)'
        col_amount = 'Montant'

        def next_page(self):
            if Link('//a[@class="pictoSuivant"]', default=None)(self):
                form = self.page.get_form(id="frm_fwk")
                form['fwkaction'] = "precSuivDet"
                form['fwkcodeaction'] = "Executer"
                form['ACTION_CHOISIE'] = "suivant"
                return requests.Request("POST", form.url, data=dict(form))

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_type = Transaction.TYPE_BANK
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = MyDecimal(TableCell('amount'))


class RibPage(LoggedPage, LCLBasePage):
    def get_iban(self):
        if (self.doc.xpath('//div[contains(@class, "rib_cadre")]//div[contains(@class, "rib_internat")]')):
            return CleanText().filter(self.doc.xpath('//div[contains(@class, "rib_cadre")]//div[contains(@class, "rib_internat")]//p//strong')[0].text).replace(' ','')


class HomePage(LoggedPage, HTMLPage):
    pass


class TransferPage(LoggedPage, HTMLPage):
    def on_load(self):
        if '"msgErreur"' in self.text:
            response = json.loads(self.text)
            raise TransferError(response['msgErreur'])

    def can_transfer(self, account_transfer_id):
        for option in self.doc.xpath('//select[@id="id_lstCptDebitablesVO"]/option'):
            if account_transfer_id in CleanText('.', replace=[(' ', '')])(option):
                return True
        return False

    def get_account_index(self, xpath, account_id):
        for option in self.doc.xpath('//select[@id="%s"]/option' % xpath):
            if account_id in CleanText('.', replace=[(' ', '')])(option):
                return option.attrib['value']
        else:
            raise TransferError("account %s not found" % account_id)

    def transfer(self, account, recipient, amount, reason):
        form = self.get_form(id='formclient')
        form.url = '/outil/UWVS/Accueil/verificationParametres'
        form['montant'] = amount
        form['lstCptDebitablesVO'] = self.get_account_index('id_lstCptDebitablesVO', account._transfer_id)
        if recipient.category == u'Interne':
            form['lstCptCreditablesVO'] = self.get_account_index('id_lstCptCreditablesVO', recipient.id)
        else:
            form['lstCptRibPreEnrVIPVO'] = self.get_account_index('lstCptRIBVIPVO', recipient.id)
            form['benef'] = recipient.label
            form['typeCptBenef'] = 'R'
        if reason:
            form['libEmetteur'] = reason
            form['libBenef'] = reason
        form.submit()

    def confirm(self, passwd):
        try:
            vk = LCLVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.exception(err)
        password = vk.get_string_code(passwd)

        for script in self.doc.findall("//script"):
            if script.text is None or len(script.text) == 0:
                continue
            m = re.search('myXOR\(\$\("#postClavier"\).val\(\), (\d)', script.text)
            if m:
                seed = int(m.group(1))
                break
        form = self.get_form(id='mainform')
        form['postClavier'] = base64.b64encode(myXOR(password, seed))
        form.submit()

    @method
    class iter_recipients(ListElement):
        item_xpath = '//select[@id="id_lstCptCreditablesVO"]/option'

        class Item(ItemElement):
            klass = Recipient
            validate = lambda self, obj: self.obj_id(self) != self.env['account_transfer_id']

            obj_id = CleanText(Regexp(CleanText('.'), ' (\d+ \d+[A-Z]+) - - -'), replace=[(' ', '')])
            obj_label = Regexp(CleanText('.'), u'(.*?) \d{5}')
            obj_bank_name = u'LCL'
            obj_category = u'Interne'
            obj_iban = NotAvailable

            def obj_enabled_at(self):
                return datetime.now().replace(microsecond=0)

    def check_data_consistency(self, account, recipient, amount, reason, offset=0):
        try:
            for index, tr in enumerate(self.doc.xpath('//table[has-class("recap")]/tr[@class="recapLigne"]')):
                if index == 0 + offset:
                    assert CleanDecimal('./td[@class="recapValeur"]', replace_dots=True)(tr) == amount
                elif index == 1 + offset:
                    assert account._transfer_id in CleanText('./td[@class="recapValeur"]', replace=[(' ', '')])(tr)
                elif index == 2 + offset and recipient.category == u'Externe':
                    assert recipient.label in CleanText('./td[@class="recapValeur"]')(tr)
                elif index == 3 + offset and recipient.category == u'Externe':
                    assert recipient.iban in CleanText('./td[@class="recapValeur"]', replace=[(' ', '')])(tr)
                elif index == 4 + offset and reason:
                    assert reason in CleanText('./td[@class="recapValeur"]')(tr)
        except AssertionError:
            raise TransferError('Something went wrong')

    def create_transfer(self, account, recipient, amount, reason):
        transfer = Transfer()
        transfer.currency = FrenchTransaction.Currency('//table[has-class("recap")]/tr[@class="recapLigne"][1]/td[@class="recapValeur"]')(self.doc)
        transfer.amount = amount
        transfer.account_iban = account.iban
        transfer.recipient_iban = recipient.iban
        transfer.account_id = account.id
        transfer.recipient_id = recipient.id
        transfer.exec_date = date.today()
        transfer.label = reason
        transfer.account_label = account.label
        transfer.recipient_label = recipient.label
        transfer._account = account
        transfer._recipient = recipient
        transfer.account_balance = account.balance
        return transfer

    def fill_transfer_id(self, transfer):
        transfer.id = str(CleanDecimal('//td[@class="recapRef"]')(self.doc))
        return transfer


class RecipientPage(LoggedPage, HTMLPage):
    @method
    class iter_recipients(TableElement):
        item_xpath = '//table[@class="tagTab pyjama"]/tbody/tr'
        head_xpath = '//table[@class="tagTab pyjama"]/thead/tr/th'

        col_iban = 'IBAN'
        col_label = u'Libellé'

        class Item(ItemElement):
            klass = Recipient

            obj_iban = obj_id = CleanText(TableCell('iban'), replace=[(' ', '')])
            obj_label = CleanText(TableCell('label'))
            obj_bank_name = NotAvailable
            obj_category = u'Externe'

            def obj_enabled_at(self):
                return datetime.now().replace(microsecond=0)

            def validate(self, el):
                assert is_iban_valid(el.iban)
                return True

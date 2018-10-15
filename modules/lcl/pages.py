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

from __future__ import unicode_literals, division

import re
import requests
import base64
import math
import random
from decimal import Decimal
from io import BytesIO
from datetime import datetime, timedelta

from weboob.capabilities import NotAvailable
from weboob.capabilities.base import find_object, Currency
from weboob.capabilities.bank import (
    Account, Investment, Recipient, TransferError, TransferBankError, Transfer,
)
from weboob.capabilities.bill import Document, Subscription, DocumentTypes
from weboob.capabilities.profile import Person, ProfileMissing
from weboob.capabilities.contact import Advisor
from weboob.browser.elements import method, ListElement, TableElement, ItemElement, SkipItem
from weboob.exceptions import ParseError
from weboob.browser.exceptions import ServerError
from weboob.browser.pages import LoggedPage, HTMLPage, FormNotFound, pagination
from weboob.browser.filters.html import Attr, Link, TableCell, AttributeNotFound
from weboob.browser.filters.standard import (
    CleanText, Field, Regexp, Format, Date, CleanDecimal, Map, AsyncLoad, Async, Env,
    Eval, Slugify,
)
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.compat import unicode
from weboob.tools.compat import urlparse, parse_qs
from weboob.tools.html import html2text
from weboob.tools.date import parse_french_date
from weboob.tools.capabilities.bank.investments import is_isin_valid


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=Decimal(0))
    return CleanDecimal(*args, **kwargs)


def myXOR(value, seed):
    s = ''
    for i in range(len(value)):
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
        self.url += "%s"%str(int(math.floor(int(random.random()*1000000000000000000000))))
        super(LCLVirtKeyboard, self).__init__(BytesIO(basepage.browser.open(self.url).content), basepage.doc,img,self.color, "id")
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
        form['postClavierXor'] = base64.b64encode(
            myXOR(password, seed).encode("utf-8")
        )
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

    def select_contract(self, id_contract=None):
        link = self.doc.xpath('//a[contains(text(), "Votre situation globale")]')
        if not id_contract and len(link):
            self.browser.location(link[0].attrib['href'])
        else:
            form = self.get_form(nr=0)
            if 'contratId' in form:
                if id_contract:
                    form['contratId'] = id_contract
                self.browser.current_contract = form['contratId']
            form.submit()


class ContractsChoicePage(ContractsPage):
    def on_load(self):
        if self.is_error():
            raise BrowserIncorrectPassword()
        self.browser.contracts = [unicode(x) for x in self.doc.xpath('//input[@name="contratId"]/@value')]
        if not self.logged and not self.browser.current_contract:
            self.select_contract()


class AccountsPage(LoggedPage, HTMLPage):
    def on_load(self):
        warn = self.doc.xpath('//div[@id="attTxt"]')
        if len(warn) > 0:
            raise BrowserIncorrectPassword(warn[0].text)

    def get_name(self):
        return CleanText('//li[@id="nomClient"]/p')(self.doc)

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
                           '004': Account.TYPE_CHECKING,
                           '005': Account.TYPE_CHECKING,
                           '006': Account.TYPE_CHECKING,
                           '007': Account.TYPE_SAVINGS,
                           '012': Account.TYPE_SAVINGS,
                           '023': Account.TYPE_CHECKING,
                           '046': Account.TYPE_SAVINGS,
                           '047': Account.TYPE_SAVINGS,
                           '049': Account.TYPE_SAVINGS,
                           '058': Account.TYPE_CHECKING,
                           '068': Account.TYPE_PEA,
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
            obj_number = Field('id')

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

    @method
    class get_advisor(ItemElement):
        klass = Advisor

        obj_name = CleanText('//div[@id="contacterMaBqMenu"]//p[@id="itemNomContactMaBq"]/span')
        obj_email = obj_mobile = obj_fax = NotAvailable
        obj_phone = Regexp(CleanText('//div[@id="contacterMaBqMenu"]//p[contains(text(), "Tel")]', replace=[(' ', '')]), '([\s\d]+)', default=NotAvailable)
        obj_agency = CleanText('//div[@id="sousContentAgence"]//p[@class="itemSousTitreMenuMaBq"][1]')

        def obj_address(self):
            address = CleanText('//div[@id="sousContentAgence"]//p[@class="itemSousTitreMenuMaBq"][2]', default=None)(self)
            city = CleanText('//div[@id="sousContentAgence"]//p[@class="itemSousTitreMenuMaBq"][3]', default=None)(self)
            return "%s %s" % (address, city) if address and city else NotAvailable


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
            obj__transfer_id = None
            obj_number = Regexp(CleanText(TableCell('id'), replace=[(' ', ''),('-', '')]), r'(\d{11}[A-Z])')

            def obj_label(self):
                has_type = CleanText('./ancestor::table[.//th[contains(text(), "Type")]]', default=None)(self)
                return CleanText('./td[2]')(self) if has_type else CleanText('./ancestor::table/preceding-sibling::div[1]')(self).split(' - ')[0]

            def parse(self, el):
                label = Field('label')(self)
                trs = self.xpath('//td[contains(text(), $label)]/ancestor::tr[1] | ./ancestor::table[1]/tbody/tr', label=label)
                i = [i for i in range(len(trs)) if el == trs[i]]
                i = i[0] if i else 0
                label = label.replace(' ', '')
                self.env['id'] = "%s%s%s" % (Regexp(CleanText(TableCell('id')), r'(\w+)\s-\s(\w+)', r'\1\2')(self), label.replace(' ', ''), i)


class LoansProPage(LoggedPage, HTMLPage):
    @method
    class get_list(TableElement):
        item_xpath = '//table[.//th[contains(text(), "Emprunteur")]]/tbody/tr[td[3]]'
        head_xpath = '//table[.//th[contains(text(), "Emprunteur")]]/thead/tr/th'
        flush_at_end = True

        col_id = re.compile('Emprunteur')
        col_balance = [u'Capital restant dû', re.compile('Sommes totales restant dues')]

        class account(ItemElement):
            klass = Account

            obj_balance = CleanDecimal(TableCell('balance'), replace_dots=True, sign=lambda x: -1)
            obj_currency = FrenchTransaction.Currency(TableCell('balance'))
            obj_type = Account.TYPE_LOAN
            obj_id = Env('id')
            obj__transfer_id = None
            obj_number = Regexp(CleanText(TableCell('id'), replace=[(' ', ''),('-', '')]), r'(\d{11}[A-Z])')

            def obj_label(self):
                has_type = CleanText('./ancestor::table[.//th[contains(text(), "Nature libell")]]', default=None)(self)
                return CleanText('./td[3]')(self) if has_type else CleanText('./ancestor::table/preceding-sibling::div[1]')(self).split(' - ')[0]

            def parse(self, el):
                label = Field('label')(self)
                trs = self.xpath('//td[contains(text(), $label)]/ancestor::tr[1] | ./ancestor::table[1]/tbody/tr', label=label)
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
            (re.compile('.*(FRAIS DE TENUE DE COMPTE).*'), FrenchTransaction.TYPE_BANK),
            (re.compile(r'.*\b(RETRAIT)\b.*'), FrenchTransaction.TYPE_WITHDRAWAL),
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
                    m = re.search(r'\d+,\d+COM (\d+,\d+)', raw)
                    if m:
                        obj.commission = -CleanDecimal(replace_dots=True).filter(m.group(1))
                elif not obj.raw:
                    # Empty transaction label
                    obj.raw = obj.label = Async('details', CleanText(u'//td[contains(text(), "Nature de l\'opération")]/following-sibling::*[1]'))(self)
                if not obj.date:
                    obj.date = Async('details', Date(CleanText(u'//td[contains(text(), "Date de l\'opération")]/following-sibling::*[1]', default=u''), default=NotAvailable))(self)
                    obj.rdate = obj.date
                    obj.vdate = Async('details', Date(CleanText(u'//td[contains(text(), "Date de valeur")]/following-sibling::*[1]', default=u''), default=NotAvailable))(self)
                    obj.amount = Async('details', CleanDecimal(u'//td[contains(text(), "Montant")]/following-sibling::*[1]', replace_dots=True, default=NotAvailable))(self)
                # ugly hack to fix broken html
                # sometimes transactions have really an amount of 0...
                if not obj.amount and CleanDecimal(TableCell('credit'), default=None)(self) is None:
                    obj.amount = Async('details', CleanDecimal(u'//td[contains(text(), "Montant")]/following-sibling::*[1]', replace_dots=True, default=NotAvailable))(self)
                return True

    @pagination
    def get_operations(self):
        return self._get_operations(self)()


class CBHistoryPage(AccountHistoryPage):
    def get_operations(self):
        for tr in self._get_operations(self)():
            tr.type = tr.TYPE_DEFERRED_CARD
            deferred_date = Regexp(CleanText('//div[@class="date"][contains(text(), "Carte")]'), r'le ([^:]+)', default=None)(self.doc)
            if deferred_date:
                tr.date = parse_french_date(deferred_date).date()
            # rdate > date doesn't make any sense but it seems that lcl website can do shitty things sometimes
            if tr.date >= tr.rdate:
                yield tr
            else:
                self.logger.error('skipping transaction with rdate > date')


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
    REFRESH_MAX = 0

    TYPES = {u'plan épargne en actions': Account.TYPE_PEA
            }

    def on_load(self):
        """
        Sometimes we are directed towards a prior html page before accessing Bourse Page.
        Submit the form to access the page that contains the Bourse Page's session cookie.
        """
        try:
            form = self.get_form(id='form')
        except FormNotFound:  # already on the targetted page
            pass
        else:
            form.submit()

        super(BoursePage, self).on_load()

    def open_iframe(self):
        # should be done always (in on_load)?
        for iframe in self.doc.xpath('//iframe[@id="mainIframe"]'):
            self.browser.location(iframe.attrib['src'])
            break

    def password_required(self):
        return CleanText(u'//b[contains(text(), "Afin de sécuriser vos transactions, nous vous invitons à créer un mot de passe trading")]')(self.doc)

    def get_next(self):
        if 'onload' in self.doc.xpath('.//body')[0].attrib:
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
        col_titres = re.compile('Valorisation')
        col_especes = u'Solde espèces'

        class item(ItemElement):
            klass = Account

            load_details = Field('_market_link') & AsyncLoad

            obj__especes = CleanDecimal(TableCell('especes'), replace_dots=True, default=0)
            obj__titres = CleanDecimal(TableCell('titres'), replace_dots=True, default=0)
            obj_valuation_diff = Async('details') &  CleanDecimal('//td[contains(text(), "value latente")]/ \
                                                                  following-sibling::td[1]', replace_dots=True)
            obj__market_link = Regexp(Attr(TableCell('label'), 'onclick'), "'(.*?)'")
            obj__link_id = Async('details') & Link(u'//a[text()="Historique"]')
            obj__transfer_id = None
            obj_balance = Field('_titres')

            def obj_currency(self):
                return Currency.get_currency(CleanText(TableCell('titres'))(self))

            def obj_number(self):
                number = CleanText((TableCell('label')(self)[0]).xpath('./div[not(b)]'))(self).replace(' - ', '')
                m = re.search(r'(\d{11,})[A-Z]', number)
                if m:
                    number = m.group(0)
                return number

            def obj_id(self):
                return "%sbourse" % Field('number')(self)

            def obj_label(self):
                return "%s Bourse" % CleanText((TableCell('label')(self)[0]).xpath('./div[b]'))(self)

            def obj_type(self):
                return self.page.TYPES.get(' '.join(Field('label')(self).split()[:-1]).lower(), Account.TYPE_MARKET)

    def get_logout_link(self):
        return Link('//a[@class="link-underline" and contains(text(), "espace client")]')(self.doc)

    @method
    class iter_investment(ListElement):
        item_xpath = '//table[@id="tableValeurs"]/tbody/tr[@id and count(descendant::td) > 1]'
        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//td[2]/div/a')
            obj_code = CleanText('.//td[2]/div/br/following-sibling::text()') & Regexp(pattern='^([^ ]+).*', default=NotAvailable)
            obj_quantity = MyDecimal('.//td[3]/span')
            obj_diff = MyDecimal('.//td[7]/span')
            obj_valuation = MyDecimal('.//td[5]')

            def obj_code_type(self):
                code = Field('code')(self)
                if code and is_isin_valid(code):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable

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
                   if self.page.doc.xpath('//*[@data-page = $page]', page=form['PAGE']) else None

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
    def on_load(self):
        try:
            # when life insurance access is restricted, a complete lcl logout form is present, don't use it
            # and sometimes there's just no form
            form = self.get_form(xpath='//form[not(@id="formLogout")]')
            form.submit()
        except FormNotFound: # Sometime no form is present, just a redirection
            self.logger.debug('no form on this page')

        super(DiscPage, self).on_load()


class NoPermissionPage(LoggedPage, HTMLPage):
    def get_error_msg(self):
        error_msg = CleanText(
            '//div[@id="divContenu"]//div[@id="attTxt" and contains(text(), "vous n\'avez pas accès à cette opération")]'
        )(self.doc)
        return error_msg


class AVPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '//table[@class]/tbody/tr'

        class item(ItemElement):
            klass = Account

            def condition(self):
                if self.obj_balance(self) == 0 and not self.el.xpath('.//td/a'):
                    self.logger.warning("ignoring an AV account because there's no link for it")
                    return False
                return True

            obj__owner = CleanText('.//td[2]')
            obj_label = Format(u'%s %s', CleanText('.//td/text()[following-sibling::br]'), obj__owner)
            obj_balance = CleanDecimal('.//td[last()]', replace_dots=True)
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj_currency = 'EUR'
            obj__link_id = None
            obj__market_link = None
            obj__coming_links = []
            obj__transfer_id = None
            obj_number = Field('id')

            def obj_id(self):
                try:
                    _id = CleanText('.//td/a/@id')(self)
                    if not _id:
                        self.page.browser.assurancevie.go()
                        ac_details_page = self.page.browser.open(Link('.//td/a')(self)).page
                    else:
                        if '-' in _id:
                            split = _id.split('-')
                            ac_details_page = self.page.browser.open('/outil/UWVI/AssuranceVie/accesDetail?ID_CONTRAT=%s&PRODUCTEUR=%s' % (split[0], split[1])).page
                        else:
                            ac_details_page = self.page.browser.open('/outil/UWVI/AssuranceVie/accesDetail?ID_CONTRAT=%s' % (_id)).page
                    return CleanText('(//tr[3])/td[2]')(ac_details_page.doc)
                except ServerError:
                    self.logger.debug("link didn't work, trying with the form instead")
                    # the above server error can cause the form to fail, so we may have to go back on the accounts list before submitting
                    self.page.browser.open(self.page.url)
                    # redirection to lifeinsurances accounts and comeback on Lcl original website
                    page = self.obj__form().submit().page
                    account_id = page.get_account_id()
                    page.come_back()
                    return account_id

            def obj__form(self):
                form_id = Attr('.//td/a', 'id', default=None)(self)
                form_class = Attr('.//td/a', 'class', default=None)(self)
                if form_id:
                    if '-' in form_id:
                        id_contrat = re.search(r'^(.*?)-', form_id).group(1)
                        producteur = re.search(r'-(.*?)$', form_id).group(1)
                    else:
                        id_contrat = form_id
                        producteur = None
                else:
                    if len(self.xpath('.//td/a[has-class("clickPopupDetail")]')):
                        # making a form of this link sometimes makes the site return an empty response...
                        # the link is a link to some info, not full AV website
                        # it's probably an indication the account is restricted anyway, so avoid it
                        self.logger.debug("account is probably restricted, don't try its form")
                        return None

                    # sometimes information are not in id but in href
                    url = Attr('.//td/a', 'href', default=None)(self)
                    parsed_url = urlparse(url)
                    params = parse_qs(parsed_url.query)

                    id_contrat = params['ID_CONTRAT'][0]
                    producteur = params['PRODUCTEUR'][0]

                if 'redirect' in form_class:
                    form = self.page.get_form('//form[@id="formRedirectPart"]')
                else:
                    form = self.page.get_form('//form[@id="formRoutage"]')
                    form['PRODUCTEUR'] = producteur
                form['ID_CONTRAT'] = id_contrat
                return form


class SendTokenPage(LoggedPage, LCLBasePage):
    def on_load(self):
        form = self.get_form('//form')
        return form.submit()


class Form2Page(LoggedPage, LCLBasePage):
    def assurancevie_hist_not_available(self):
        msg = "Ne détenant pas de compte dépôt chez LCL, l'accès à ce service vous est indisponible"
        return msg in CleanText('//div[@id="attTxt"]')(self.doc)

    def is_restricted(self):
        return self.assurancevie_hist_not_available()

    def on_load(self):
        if self.assurancevie_hist_not_available():
            return
        error = CleanText('//div[@id="attTxt"]/text()[1]')(self.doc)
        if "L’accès au service est momentanément indisponible" in error:
            raise BrowserUnavailable(error)

        form = self.get_form(name="formulaire")
        cName = self.get_from_js('.cName.value  = "', '";')
        if cName:
            form['cName'] = cName
            form['cValue'] = self.get_from_js('.cValue.value  = "', '";')
            form['cMaxAge'] = '-1'
        return form.submit()


class CaliePage(LoggedPage, HTMLPage):
    def on_load(self):
        # TODO raise the ActionNeeded when backend handles it.
        if self.doc.xpath('//button[@id="acceptDisclaimerButton"]'):
            self.logger.warning('Action Needed on website: %s', CleanText('//div[@class="data-header"]')(self.doc))


class AVDetailPage(LoggedPage, LCLBasePage):
    def get_account_id(self):
        return Regexp(CleanText('//div[@class="libelletitrepage"]/h1'), r"N° (\w+)")(self.doc)

    def sub(self):
        form = self.get_form(name="formulaire")
        cName = self.get_from_js('.cName.value  = "', '";')
        if cName:
            form['cName'] = cName
            form['cValue'] = self.get_from_js('.cValue.value  = "', '";')
            form['cMaxAge'] = '-1'
        return form.submit()

    def submit_simple(self):
        form = self.get_form(name="formulaire")
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
        return self.browser.location('https://assurance-vie-et-prevoyance.secure.lcl.fr/filiale/entreeBam', params=params)

    def get_details(self, account, act=None):
        form = self.get_form(id="frm_fwk")
        form.submit()
        if act is not None:
            self.browser.location("entreeBam?sessionSAG=%s&act=%s" % (form['sessionSAG'], act))

    def is_restricted(self):
        msg = CleanText('//div[has-class("titre_libelle_erreur")]')(self.doc)
        return msg in (
            "Pour ce type d’opération, nous vous conseillons de vous rapprocher de votre conseiller afin de bénéficier du conseil personnalisé le mieux adapté à vos objectifs.",
            "Vous n’avez pas accès à l’espace assurances de personnes.",
        )

    @method
    class iter_investment(TableElement):
        head_xpath = '//table[@class="table"][ends-with(@id,"CD_UCT")]/thead//th'
        item_xpath = '//table[@class="table"][ends-with(@id,"CD_UCT")]/tbody/tr'

        col_label = 'Le(s) support(s) financier(s) de votre contrat'
        col_unitvalue = 'Valeur de la part'
        col_vdate = 'En date du :'
        col_quantity = 'Nombre de parts'
        col_valuation = 'Total'
        col_portfolio_share = u'Répartition'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))

            def obj_code(self):
                td = TableCell('label')(self)[0]
                return Attr('.//a', 'id', default=NotAvailable)(td)

            obj_code_type = Investment.CODE_TYPE_ISIN

            def obj_quantity(self):
                return MyDecimal(TableCell('quantity'))(self) or NotAvailable

            def obj_unitvalue(self):
                return MyDecimal(TableCell('unitvalue'))(self) or NotAvailable

            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal(TableCell('portfolio_share'), replace_dots=True))

            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)

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

    def check_iban_by_account(self, account_id):
        iban_account_id = CleanText().filter(self.doc.xpath('(//td[@class[contains(., "guichet-")]]/following-sibling::*)[1]/strong'))
        iban_guichet_id = CleanText().filter(self.doc.xpath('(//td[@class[contains(., "guichet-")]]/strong)[1]'))
        iban_account = "%s%s" % (iban_guichet_id, iban_account_id[4:])

        if account_id == iban_account:
            return CleanText().filter(self.doc.xpath('//div[contains(@class, "rib_cadre")]//div[contains(@class, "rib_internat")]//p//strong')[0].text).replace(' ', '')
        else:
            return None

    def has_iban_choice(self):
        return False if self.doc.xpath('(//strong[contains(., "RELEVE D\'IDENTITE BANCAIRE")])[1]') else True

class HomePage(LoggedPage, HTMLPage):
    pass


class TransferPage(LoggedPage, HTMLPage):
    def on_load(self):
        # This aims to track input errors.
        script_error = CleanText(u"//script[contains(text(), 'if (\"true\"===\"true\")')]")(self.doc)
        if script_error:
            raise TransferBankError(CleanText().filter(html2text(re.search(u'\.html\("(.*?)"\)', script_error).group(1))))

    def can_transfer(self, account_transfer_id):
        for div in self.doc.xpath('//div[input[@id="indexCompteEmetteur"]]//div[@class="infoCompte" and not(@title)]'):
            if account_transfer_id in CleanText('.', replace=[(' ', '')])(div):
                return True
        return False

    def get_account_index(self, xpath, account_id):
        for option in self.doc.xpath('//select[@id=$id]/option', id=xpath):
            if account_id in CleanText('.', replace=[(' ', '')])(option):
                return option.attrib['value']
        else:
            raise TransferError("account %s not found" % account_id)

    def choose_recip(self, recipient):
        form = self.get_form(id='formulaire')
        form['indexCompteDestinataire'] = self.get_value(recipient._transfer_id, 'recipient')
        form.submit()

    def transfer(self, amount, reason):
        form = self.get_form(id='formulaire')
        form['libMontant'] = amount
        form['motifVirement'] = reason
        form.submit()

    def deferred_transfer(self, amount, reason, exec_date):
        form = self.get_form(id='formulaire')
        form['libMontant'] = amount
        form['motifVirement'] = reason
        form['libDateProg'] = exec_date.strftime('%d/%m/%Y')
        form['dateFinVirement'] = 'N'
        form['frequenceVirement'] = 'UD'
        form['premierJourVirementProg'] = '01'
        form['typeVirement'] = 'Programme'
        form.submit()

    def get_id_from_response(self, acc):
        id_xpath = '//div[@id="contenuPageVirement"]//div[@class="infoCompte" and not(@title)]'
        acc_ids = [CleanText('.')(acc_id) for acc_id in self.doc.xpath(id_xpath)]
        # there should have 2 ids, one for account and one for recipient
        assert len(acc_ids) == 2

        for index, acc_id in enumerate(acc_ids):
            _id = acc_id.split(' ')
            if len(_id) == 2:
                # to match with weboob account id
                acc_ids[index] = _id[0] + _id[1][4:]

        if acc == 'account':
            return acc_ids[0]
        return acc_ids[1]

    def handle_response(self, account, recipient):
        transfer = Transfer()

        transfer._account = account
        transfer.account_id = self.get_id_from_response('account')
        transfer.account_iban = account.iban
        transfer.account_label = account.label
        transfer.account_balance = account.balance
        assert account._transfer_id in CleanText(
            u'//div[div[@class="libelleChoix" and contains(text(), "Compte émetteur")]] \
            //div[@class="infoCompte" and not(@title)]', replace=[(' ', '')]
        )(self.doc)

        transfer._recipient = recipient
        transfer.recipient_id = self.get_id_from_response('recipient')
        transfer.recipient_iban = recipient.iban
        transfer.recipient_label = recipient.label
        assert recipient._transfer_id in CleanText(
            u'//div[div[@class="libelleChoix" and contains(text(), "Compte destinataire")]] \
            //div[@class="infoCompte" and not(@title)]', replace=[(' ', '')]
        )(self.doc)

        transfer.currency = FrenchTransaction.Currency('//div[@class="topBox"]/div[@class="montant"]')(self.doc)
        transfer.amount = CleanDecimal('//div[@class="topBox"]/div[@class="montant"]', replace_dots=True)(self.doc)
        transfer.exec_date = Date(
            Regexp(CleanText('//div[@class="topBox"]/div[@class="date"]'), r'(\d{2}\/\d{2}\/\d{4})'),
            dayfirst=True
        )(self.doc)
        # skip html comment with filtering on text() content
        transfer.label = CleanText('//div[@class="motif"]/text()[contains(., "Motif : ")]',
                                   replace=[('Motif : ','')])(self.doc)

        return transfer

    def confirm(self):
        form = self.get_form(id='formulaire')
        form.submit()

    def get_value(self, _id, value_type):
        for div in self.doc.xpath('//div[@onclick]'):
            if _id in CleanText('.//div[not(@title)]', replace=[(' ', '')])(div):
                return Regexp(Attr('.', 'onclick'), '(\d+)')(div)
        raise TransferError('Could not find %s account.' % value_type)

    def choose_origin(self, account_transfer_id):
        form = self.get_form()
        form['indexCompteEmetteur'] = self.get_value(account_transfer_id, 'origin')
        form.submit()

    @method
    class iter_recipients(ListElement):
        item_xpath = '//div[@id="listeDestinataires"]//div[@class="pointeur cardCompte"]'

        class Item(ItemElement):
            klass = Recipient
            validate = lambda self, obj: self.obj_id(self) != self.env['account_transfer_id']

            obj_id = CleanText('./div[@class="infoCompte" and not(@title)]', replace=[(' 0000', '')])
            obj__transfer_id = CleanText('./div[@class="infoCompte" and not(@title)]', replace=[(' ', '')])
            obj_label = CleanText('./div[1]')
            obj_bank_name = Env('bank_name')
            obj_category = Env('category')
            obj_iban = Env('iban')

            def obj_enabled_at(self):
                return datetime.now().replace(microsecond=0)

            def condition(self):
                return len(self.el.xpath('./div')) > 1

            def parse(self, el):
                if bool(CleanText('./div[@id="soldeEurosCompte"]')(self)):
                    self.env['category'] = u'Interne'
                    account = find_object(self.page.browser.get_accounts_list(), id=self.obj_id(self))
                    self.env['iban'] = account.iban if account else NotAvailable
                    self.env['bank_name'] = u'LCL'
                else:
                    self.env['category'] = u'Externe'
                    self.env['iban'] = self.obj_id(self)
                    self.env['bank_name'] = NotAvailable

    def fill_transfer_id(self, transfer):
        transfer.id = Regexp(CleanText(u'//div[@class="alertConfirmationVirement"]//p[contains(text(), "référence")]'), u'référence (\d+)')(self.doc)
        return transfer


class AddRecipientPage(LoggedPage, HTMLPage):
    def validate(self, iban, label):
        form = self.get_form(id='mainform')
        form['PAYS_IBAN'] = iban[:2]
        form['LIBELLE'] = label
        form['COMPTE_IBAN'] = iban[2:]
        form.submit()


class CheckValuesPage(LoggedPage, HTMLPage):
    def check_values(self, iban, label):
        values = CleanText('//form[contains(@action, "/outil")]')(self.doc)
        assert iban in values, 'Iban (%s) not found in values: %s' % (iban, values)
        assert label in values, 'Recipient label (%s) not found in values: %s' % (label, values)


class DocumentsPage(LoggedPage, HTMLPage):
    def do_search_request(self):
        form = self.get_form(id="rechercherForm")
        form['listePeriode'] = "PERIODE1"
        form['listeFamille'] = "ALL"
        form['debutRec'] = None
        form['finRec'] = None
        form['typeDocFamHidden'] = "ALL"
        form['typeDocSFamHidden'] = None
        form.submit()

    @method
    class get_list(TableElement):
        head_xpath = '//table[@class="dematTab"]/thead/tr/th'
        item_xpath = u'//table[@class="dematTab"]/tbody/tr[./td[@class="dematTab-firstCell"]]'

        col_label = 'Nature de document'
        col_id = 'Type de document'
        col_url = 'Visualiser'
        col_date = 'Date'

        class item(ItemElement):
            klass = Document

            obj_id = Slugify(Format('%s_%s', CleanText(TableCell('id')), CleanText(TableCell('date'))))
            obj_label = Format('%s %s', CleanText(TableCell('label')), CleanText(TableCell('date')))
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_format = "pdf"

            def obj_url(self):
                return Link(TableCell('url')(self)[0].xpath('./a'))(self)

            def obj_type(self):
                if 'Relevé' in Field('label')(self):
                    return DocumentTypes.STATEMENT
                elif 'Bourse' in Field('label')(self):
                    return DocumentTypes.REPORT
                elif ('information' in Field('id')(self)) or ('avis' in Field('id')(self)):
                    return DocumentTypes.NOTICE
                else:
                    return DocumentTypes.OTHER


class ClientPage(LoggedPage, HTMLPage):
    @method
    class get_item(ItemElement):
        klass = Subscription

        obj_id = CleanText('//li[@id="nomClient"]', replace=[('M', ''), ('Mme', ''), (' ', '')])
        obj_label = CleanText('//li[@id="nomClient"]', replace=[('M', ''), ('Mme', '')])
        obj_subscriber = CleanText('//li[@id="nomClient"]', replace=[('M', ''), ('Mme', '')])


class RecipConfirmPage(CheckValuesPage):
    pass


class RecipientPage(LoggedPage, HTMLPage):
    pass


class SmsPage(LoggedPage, HTMLPage):
    pass


class RecipRecapPage(CheckValuesPage):
    pass


class ProfilePage(LoggedPage, HTMLPage):
    def get_profile(self, name):
        error_xpath = '//div[contains(text(), "Nous vous invitons à prendre contact avec votre conseiller")]'
        if self.doc.xpath(error_xpath):
            raise ProfileMissing(CleanText(error_xpath, children=False)(self.doc))

        profile = Person()
        profile.name = name
        try:
            profile.email = Attr('//input[@id="textMail"]', 'value')(self.doc)
        except AttributeNotFound:
            pass
        nb = Attr('//input[@id="nbEnfant"]', 'value', default=NotAvailable)(self.doc)
        if nb:
            profile.children = Decimal(nb)
        return profile


class DepositPage(LoggedPage, HTMLPage):
    @method
    class get_list(TableElement):
        head_xpath = '//table/thead/tr/th'
        item_xpath = '//table/tbody/tr[not(@class="tableTrSolde")]'

        col_owner = 'Titulaire'
        col_name = 'Nom du contrat'
        col_balance = 'Capital investi'

        class item(ItemElement):
            klass = Account

            obj_type = Account.TYPE_DEPOSIT
            obj_label = Format('%s %s', CleanText(TableCell('name')), CleanText(TableCell('owner')))
            obj_balance = MyDecimal(TableCell('balance'))
            obj_currency = 'EUR'
            obj__contract = CleanText(TableCell('name'))
            obj__link_index = Regexp(CleanText('.//a/@id'), r'(\d+)')
            # So it can be modified later
            obj_id = None
            obj__transfer_id = None

    def set_deposit_account_id(self, account):
        account.id = CleanText('//td[contains(text(), "N° contrat")]/following::td[1]//b')(self.doc)

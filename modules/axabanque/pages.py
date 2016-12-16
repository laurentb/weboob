# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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
from decimal import Decimal, InvalidOperation
from cStringIO import StringIO

from weboob.exceptions import BrowserBanned, BrowserUnavailable
from weboob.browser.pages import HTMLPage, RawPage, JsonPage, PDFPage, LoggedPage
from weboob.browser.elements import ItemElement, ListElement, TableElement, method
from weboob.browser.filters.standard import CleanText, Date, CleanDecimal, Field, BrowserURL, \
                                            TableCell, Async, AsyncLoad, Regexp
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import VirtKeyboard, VirtKeyboardError
from weboob.tools.ordereddict import OrderedDict


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class MyVirtKeyboard(VirtKeyboard):
    margin = 5, 5, 5, 5
    color = (255, 255, 255)

    symbols = {'0': '6959163af44cc50b3863e7e306d6e571',
               '1': '98b32dff471e903b6fa8e3a0f1544b17',
               '2': '32722d5b6572f9d46350aca7fb66263a',
               '3': '835a9c8bf66e28f3ffa2b12994bc3f9a',
               '4': 'e7457342c434da4fb0fd974f7dc37002',
               '5': 'c8b74429a805e12a08c5ed87fd9730ce',
               '6': '70a84c766bc323343c0c291146f652db',
               '7': 'e4e7fb4f8cc90c8ad472906b5eceeb99',
               '8': 'ffb78dbea5a171990e14d707d4772ba2',
               '9': '063dcb4179beaeff60fb73c80cbd429d'
              }

    coords = {'0': (0, 0, 40, 40),
              '1': (40, 0, 80, 40),
              '2': (80, 0, 120, 40),
              '3': (120, 0, 160, 40),
              '4': (0, 40, 40, 80),
              '5': (40, 40, 80, 80),
              '6': (80, 40, 120, 80),
              '7': (120, 40, 160, 80),
              '8': (0, 80, 40, 120),
              '9': (40, 80, 80, 120),
              '10': (80, 80, 120, 120),
              '11': (120, 80, 160, 120),
              '12': (0, 120, 40, 160),
              '13': (40, 120, 80, 160),
              '14': (80, 120, 120, 160),
              '15': (120, 120, 160, 160)
             }

    def __init__(self, page):
        VirtKeyboard.__init__(self, StringIO(page.content), self.coords, self.color, convert='RGB')

        self.check_symbols(self.symbols, None)

    def get_string_code(self, string):
        return ','.join(self.get_position_from_md5(self.symbols[c]) for c in string)

    def get_position_from_md5(self, md5):
        for k, v in self.md5.iteritems():
            if v == md5:
                return k

    def check_color(self, pixel):
        return pixel[0] > 0


class KeyboardPage(RawPage):
    def get_password(self, password):
        vk_passwd = None

        try:
            vk = MyVirtKeyboard(self)
            vk_passwd = vk.get_string_code(password)
        except VirtKeyboardError as e:
            self.logger.error(e)

        return vk_passwd


class LoginPage(JsonPage):
    def check_error(self):
        return (not Dict('errors')(self.doc)) is False


class PredisconnectedPage(HTMLPage):
    def on_load(self):
        raise BrowserBanned()


class InvestmentTransaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<text>Versement|versement.*)'),  FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>(Arbitrage|Prélèvement(s).*))'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>Retrait.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class InvestmentPage(LoggedPage, HTMLPage):
    TYPES = {u'Assurance vie Arpèges': Account.TYPE_LIFE_INSURANCE,
             'Epargne Retraite  PERP PAIR': Account.TYPE_SAVINGS}

    @method
    class iter_accounts(ListElement):
        item_xpath = '//section[has-class("cards") and has-class("contracts")]/article[has-class("card")]'

        class item(ItemElement):
            klass = Account

            obj_id = Regexp(CleanText('.//h2/small'), r'#(.*)')
            obj_balance = MyDecimal('.//span[@class="card-amount"]', default=NotAvailable)
            obj_iban = NotAvailable
            obj_valuation_diff = MyDecimal('.//p[@class="card-description"]')
            obj_label = CleanText('.//h2/text()')
            obj__acctype = "investment"

            def obj__aid(self):
                return Regexp(Attr('//a[@class="menu-item" and @href="%s"]' % Attr('.', 'data-redirect')(self), 'data-target'), \
                              r'aid_(.*).html')(self)

            def obj_type(self):
                return self.page.TYPES.get(Field('label')(self), Account.TYPE_UNKNOWN)

            def condition(self):
                return Field('balance')(self) is not NotAvailable

    @method
    class iter_history(ListElement):
        item_xpath = "//div[has-class('t-data')]"

        class item(ItemElement):
            klass = InvestmentTransaction

            load_details = Field('_url') & AsyncLoad

            obj_label = CleanText('(.//div[has-class("t-data__label")])[1]')
            obj_raw = InvestmentTransaction.Raw(Field('label'))
            obj_date = Date(CleanText('(.//div[has-class("t-data__date")])[1]'), dayfirst=True)
            obj_amount = MyDecimal('(.//div[has-class("t-data__amount")])[1]')
            obj__hasinv = True

            def obj__url(self):
                return '%s%s' % (BrowserURL('investment')(self), Attr('.', 'data-url')(self))

            def obj_investments(self):
                inv_page = Async('details').loaded_page(self)

                return list(inv_page.iter_investments())

    @method
    class iter_investments(ListElement):
        item_xpath = "//div[@class='white-bg']/following-sibling::div[not(@*)]"

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//div[@class="t-data__label"]')
            obj_portfolio_share = MyDecimal('.//div[has-class("t-data__amount_label")]')
            obj_valuation = MyDecimal('.//div[has-class("t-data__amount") and has-class("desktop")]')


class UnavailablePage(HTMLPage):
    def on_load(self):
        raise BrowserUnavailable()


class MyHTMLPage(HTMLPage):
    def get_view_state(self):
        return self.doc.xpath('//input[@name="javax.faces.ViewState"]')[0].attrib['value']

    def is_password_expired(self):
        return len(self.doc.xpath('//div[@id="popup_client_modifier_code_confidentiel"]'))

    def parse_number(self, number):
        # For some client they randomly displayed 4,115.00 and 4 115,00.
        # Browser is waiting for for 4 115,00 so we format the number to match this.
        if '.' in number and len(number.split('.')[-1]) == 2:
            return number.replace(',', ' ').replace('.', ',')
        return number

    def js2args(self, s):
        args = {}
        # For example:
        # noDoubleClic(this);;return oamSubmitForm('idPanorama','idPanorama:tableaux-comptes-courant-titre:0:tableaux-comptes-courant-titre-cartes:0:_idJsp321',null,[['paramCodeProduit','9'],['paramNumContrat','12234'],['paramNumCompte','12345678901'],['paramNumComptePassage','1234567890123456']]);
        for sub in re.findall("\['([^']+)','([^']+)'\]", s):
            args[sub[0]] = sub[1]

        sub = re.search('oamSubmitForm.+?,\'([^:]+).([^\']+)', s)
        args['%s:_idcl' % sub.group(1)] = "%s:%s" % (sub.group(1), sub.group(2))
        args['%s_SUBMIT' % sub.group(1)] = 1

        return args


class BankAccountsPage(LoggedPage, MyHTMLPage):
    ACCOUNT_TYPES = OrderedDict((
        ('visa',               Account.TYPE_CARD),
        ('courant-titre',      Account.TYPE_CHECKING),
        ('courant',            Account.TYPE_CHECKING),
        ('livret',             Account.TYPE_SAVINGS),
        ('ldd',                Account.TYPE_SAVINGS),
        ('pel',                Account.TYPE_SAVINGS),
        ('pea',                Account.TYPE_MARKET),
        ('titres',             Account.TYPE_MARKET),
    ))

    def get_tabs(self):
        links = self.doc.xpath('//strong[text()="Mes Comptes"]/following-sibling::ul//a/@href')
        links.insert(0, "-comptes")
        return list(set([re.findall('-([a-z]+)', x)[0] for x in links]))

    def has_accounts(self):
        return self.doc.xpath('//table[not(@id) and contains(@class, "table-produit")]')

    def get_pages(self, tab):
        pages = []
        pages_args = []
        if len(self.has_accounts()) == 0:
            table_xpath = '//table[contains(@id, "%s")]' % tab
            links = self.doc.xpath('%s//td[1]/a[@onclick and contains(@onclick, "noDoubleClic")]' % table_xpath)
            if len(links) > 0:
                form_xpath = '%s/ancestor::form[1]' % table_xpath
                form = self.get_form(form_xpath, submit='%s//input[1]' % form_xpath)
                data = {k: v for k, v in dict(form).items() if v}
                for link in links:
                    d = self.js2args(link.attrib['onclick'])
                    d.update(data)
                    pages.append(self.browser.location(form.url, data=d).page)
                    pages_args.append(d)
        else:
            pages.append(self)
            pages_args.append(None)
        return zip(pages, pages_args)

    def get_list(self):
        for table in self.has_accounts():
            tds = table.xpath('./tbody/tr')[0].findall('td')
            if len(tds) < 3:
                continue

            boxes = table.xpath('./tbody//tr[not(.//strong[contains(text(), "Total")])]')
            foot = table.xpath('./tfoot//tr')

            for box in boxes:
                account = Account()

                if len(box.xpath('.//a')) != 0 and 'onclick' in box.xpath('.//a')[0].attrib:
                    args = self.js2args(box.xpath('.//a')[0].attrib['onclick'])
                    account.label =  u'{0} {1}'.format(unicode(table.xpath('./caption')[0].text.strip()), unicode(box.xpath('.//a')[0].text.strip()))
                elif len(foot[0].xpath('.//a')) != 0 and 'onclick' in foot[0].xpath('.//a')[0].attrib:
                    args = self.js2args(foot[0].xpath('.//a')[0].attrib['onclick'])
                    account.label =  unicode(table.xpath('./caption')[0].text.strip())
                else:
                    continue

                self.logger.debug('Args: %r' % args)
                if 'paramNumCompte' not in args:
                    try:
                        label = unicode(table.xpath('./caption')[0].text.strip())
                    except Exception:
                        label = 'Unable to determine'
                    self.logger.warning('Unable to get account ID for %r' % label)
                    continue
                try:
                    account.id = args['paramNumCompte'] + args['paramNumContrat']
                    if 'Visa' in account.label:
                        card_id = re.search('(\d+)', box.xpath('./td[2]')[0].text.strip())
                        if card_id:
                            account.id += card_id.group(1)
                    if 'Valorisation' in account.label or u'Liquidités' in account.label:
                        account.id += args[next(k for k in args.keys() if "_idcl" in k)].split('Jsp')[-1]

                except KeyError:
                    account.id = args['paramNumCompte']

                for l in table.attrib['class'].split(' '):
                    if 'tableaux-comptes-' in l:
                        account_type_str =  l[len('tableaux-comptes-'):].lower()
                        break
                else:
                    account_type_str = ''

                for pattern, type in self.ACCOUNT_TYPES.iteritems():
                    if pattern in account_type_str or pattern in account.label.lower():
                        account.type = type
                        break
                else:
                    account.type = Account.TYPE_UNKNOWN

                account.type = Account.TYPE_MARKET if "Valorisation" in account.label else \
                               Account.TYPE_CARD if "Visa" in account.label else \
                               account.type

                currency_title = table.xpath('./thead//th[@class="montant"]')[0].text.strip()
                m = re.match('Montant \((\w+)\)', currency_title)
                if not m:
                    self.logger.warning('Unable to parse currency %r' % currency_title)
                else:
                    account.currency = account.get_currency(m.group(1))

                try:
                    account.balance = Decimal(FrenchTransaction.clean_amount(self.parse_number(u''.join([txt.strip() for txt in box.cssselect("td.montant")[0].itertext()]))))
                except InvalidOperation:
                    #The account doesn't have a amount
                    pass
                account._args = args
                account._acctype = "bank"
                account._hasinv = True if "Valorisation" in account.label else False
                account._url = self.doc.xpath('//form[contains(@action, "panorama")]/@action')[0]
                yield account


class IbanPage(PDFPage):
    def get_iban(self):
        iban = u''
        for part in re.findall(r'0 -273.46 Td /F\d 10 Tf \((\d+|\w\w\d\d)\)', self.doc, flags=re.MULTILINE):
            iban += part
        return iban[:len(iban)/2]


class BankTransaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RET(RAIT) DAB (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(CARTE|CB ETRANGER) (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>VIR(EMEN)?T? (SEPA)?(RECU|FAVEUR)?)( /FRM)?(?P<text>.*)'),
                                                              FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)( \d+)?$'),    FrenchTransaction.TYPE_ORDER),
                (re.compile('^(CHQ|CHEQUE) .*$'),             FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(CONVENTION \d+ |F )?COTIS(ATION)? (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),          FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                              FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                              FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(LoggedPage, MyHTMLPage):
    COL_DATE = 0
    COL_TEXT = 1
    COL_DEBIT = 2
    COL_CREDIT = 3

    def check_error(self):
        error = CleanText(default="").filter(self.doc.xpath('//p[@class="question"]'))
        return error if u"a expiré" in error else None

    def go_action(self, action):
        names = {'investment': "Portefeuille", 'history': "Mouvements"}
        for li in self.doc.xpath('//div[@class="onglets"]/ul/li[not(script)]'):
            if not Attr('.', 'class', default=None)(li) and names[action] in CleanText('.')(li):
                url = Attr('./ancestor::form[1]', 'action')(li)
                args = self.js2args(Attr('./a', 'onclick')(li))
                args['javax.faces.ViewState'] = self.get_view_state()
                self.browser.location(url, data=args)
                break

    @method
    class iter_investment(TableElement):
        item_xpath = '//table[contains(@id, "titres") or contains(@id, "OPCVM")]/tbody/tr'
        head_xpath = '//table[contains(@id, "titres") or contains(@id, "OPCVM")]/thead/tr/th[not(caption)]'

        col_label = u'Intitulé'
        col_quantity = u'NB'
        col_unitprice = re.compile(u'Prix de revient')
        col_unitvalue = u'Dernier cours'
        col_diff = re.compile(u'\+/\- Values latentes')
        col_valuation = re.compile(u'Montant')

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_quantity = CleanDecimal(TableCell('quantity'))
            obj_unitprice = CleanDecimal(TableCell('unitprice'))
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'))
            obj_valuation = CleanDecimal(TableCell('valuation'))
            obj_diff = CleanDecimal(TableCell('diff'))

            def obj_code(self):
                onclick = Attr(None, 'onclick').filter((TableCell('label')(self)[0]).xpath('.//a'))
                m = re.search(',\s+\'([^\'_]+)', onclick)
                return NotAvailable if not m else m.group(1)

            def condition(self):
                return CleanText(TableCell('valuation'))(self)

    def more_history(self):
        link = None
        for a in self.doc.xpath('.//a'):
            if a.text is not None and a.text.strip() == 'Sur les 6 derniers mois':
                link = a
                break

        form = self.doc.xpath('//form')[-1]
        if not form.attrib['action']:
            return None

        if link is None:
            # this is a check account
            args = {'categorieMouvementSelectionnePagination': 'afficherTout',
                    'nbLigneParPageSelectionneHautPagination': -1,
                    'nbLigneParPageSelectionneBasPagination': -1,
                    'nbLigneParPageSelectionneComponent': -1,
                    'idDetail:btnRechercherParNbLigneParPage': '',
                    'idDetail_SUBMIT': 1,
                    'javax.faces.ViewState': self.get_view_state(),
                   }
        else:
            # something like a PEA or so
            value = link.attrib['id']
            id = value.split(':')[0]
            args = {'%s:_idcl' % id: value,
                    '%s:_link_hidden_' % id: '',
                    '%s_SUBMIT' % id: 1,
                    'javax.faces.ViewState': self.get_view_state(),
                    'paramNumCompte': '',
                   }

        self.browser.location(form.attrib['action'], data=args)
        return True

    def get_history(self):
        #DAT account can't have transaction
        if self.doc.xpath('//table[@id="table-dat"]'):
            return
        #These accounts have investments, no transactions
        if self.doc.xpath('//table[@id="InfosPortefeuille"]'):
            return
        tables = self.doc.xpath('//table[@id="table-detail-operation"]')
        if len(tables) == 0:
            tables = self.doc.xpath('//table[@id="table-detail"]')
        if len(tables) == 0:
            tables = self.doc.getroot().cssselect('table.table-detail')
        if len(tables) == 0:
            assert len(self.doc.xpath('//td[has-class("no-result")]')) > 0
            return

        for tr in tables[0].xpath('.//tr'):
            tds = tr.findall('td')
            if len(tds) < 4:
                continue

            t = BankTransaction()
            date = u''.join([txt.strip() for txt in tds[self.COL_DATE].itertext()])
            raw = u''.join([txt.strip() for txt in tds[self.COL_TEXT].itertext()])
            debit = self.parse_number(u''.join([txt.strip() for txt in tds[self.COL_DEBIT].itertext()]))
            credit = self.parse_number(u''.join([txt.strip() for txt in tds[self.COL_CREDIT].itertext()]))

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)

            yield t


class CBTransactionsPage(TransactionsPage):
    COL_CB_CREDIT = 2

    def get_history(self):
        tables = self.doc.xpath('//table[@id="idDetail:dataCumulAchat"]')
        transactions = list()

        if len(tables) == 0:
            return transactions
        for tr in tables[0].xpath('.//tr'):
            tds = tr.findall('td')
            if len(tds) < 3:
                continue

            t = BankTransaction()
            date = u''.join([txt.strip() for txt in tds[self.COL_DATE].itertext()])
            raw = self.parse_number(u''.join([txt.strip() for txt in tds[self.COL_TEXT].itertext()]))
            credit = self.parse_number(u''.join([txt.strip() for txt in tds[self.COL_CB_CREDIT].itertext()]))
            debit = ""

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)
            transactions.append(t)

        for histo in super(CBTransactionsPage, self).get_history():
            transactions.append(histo)

        transactions.sort(key=lambda transaction: transaction.date, reverse=True)
        return iter(transactions)

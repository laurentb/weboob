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
import urllib
from decimal import Decimal, InvalidOperation
from cStringIO import StringIO
import requests

from weboob.exceptions import BrowserBanned, BrowserUnavailable
from weboob.browser.pages import HTMLPage, RawPage, JsonPage, PDFPage, LoggedPage, pagination
from weboob.browser.elements import ItemElement, TableElement, SkipItem, method
from weboob.browser.filters.standard import CleanText, Date, CleanDecimal, Env, BrowserURL, TableCell, Async, AsyncLoad, Eval
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard
from weboob.tools.ordereddict import OrderedDict


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class MyVirtKeyboard(MappedVirtKeyboard):
    margin = 2, 2, 2, 2

    symbols = {'0':'e2df31c137e6c6cb214f92f7d6cd590a',
               '1':'6057c05937af4574ff453956fbbd2e0e',
               '2':'5ea5a38efacd3977f17bbc7af83a1943',
               '3':'560a86b430d2c77e1bd9688efa1b08f9',
               '4':'e6b6b156ea34a8ae9304526e091b2960',
               '5':'914483946ee0e55bcc732fce09a0b7c0',
               '6':'c2382b8f56a0d902e9b399037a9052b5',
               '7':'c5294f8154a1407560222ac894539d30',
               '8':'fa1f25a1d5a674dd7bc0d201413d7cfe',
               '9':'7658424ff8ab127d27e08b7b9b14d331'
              }

    color = (0xFF, 0xFF, 0xFF, 0x0)

    def __init__(self, img_file, doc, img):
        MappedVirtKeyboard.__init__(self, img_file, doc, img, self.color)
        self.check_symbols(self.symbols, None)

    def get_symbol_code(self,md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self,md5sum)
        return code[-3:-2]

    def get_string_code(self,string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

    def check_color(self, pixel):
        step = 10
        return abs(pixel[0] - self.color[0]) < step and abs(pixel[1] - self.color[1]) < step and abs(pixel[2] - self.color[2]) < step


class KeyboardPage(HTMLPage):
    def get_data(self, login, password):
        key = Attr(None, 'value').filter(self.doc.xpath('//input'))
        img = self.doc.xpath('//img')[0]
        img_file = StringIO(self.browser.open('.sendvirtualkeyboard.png?key=%s' % key).content)

        data = {'login':        login,
                'password':     MyVirtKeyboard(img_file, self.doc, img).get_string_code(password),
                'key':          key,
                'vsupActive':   'false',
               }

        return data


class LoginPage(JsonPage):
    def check_error(self):
        label, tokens, error = {}, {}, None
        # Get labels
        label['bank'] = self.doc['statusBanque']['statusBanqueLibelle']
        label['investment'] = self.doc['statusAssurance']['statusAssuranceLibelle']
        # Get tokens
        tokens['bank'] = self.doc['customerInfo']['tokenBanque'] \
                         if "customerInfo" in self.doc else None
        tokens['investment'] = self.doc['customerInfo']['tokenAssurance'] \
                               if "customerInfo" in self.doc else None
        # Check if tokens are available
        if not tokens['bank'] and not tokens['investment']:
            error = label['bank'] if label['bank'] else label['investment']
        # Check insurance password status
        if self.doc['assurancePasswordChangeRequired'] is True:
            error = "Veuillez modifier votre code confidentiel."
        # At least one token ? So we update browser tokens
        self.browser.tokens = tokens
        return error


class PredisconnectedPage(HTMLPage):
    def on_load(self):
        raise BrowserBanned()


class InvestmentActivatePage(RawPage):
    pass


class InvestmentCguPage(HTMLPage):
    pass


class InvestmentTransaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<text>Versement.*)'),  FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>(Arbitrage|Prélèvements.*))'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>Retrait.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class InvestmentPage(LoggedPage, HTMLPage):
    TYPES = {'assurance vie': Account.TYPE_LIFE_INSURANCE}

    def get_home(self):
        form = self.get_form('//form')
        form['__CALLBACKID'] = "__Page"
        form['__CALLBACKPARAM'] = "on load"
        form.submit()

    def get_forms(self):
        m = re.findall('create\(([^\)]+)', CleanText().filter(self.doc.xpath( \
                       '//script[contains(text(), "Application.add")]')))
        posts = [el for el in m if "CategorieId" in el]
        forms = []
        for post in posts:
            m = re.search(('Parameters[^[]+([^]]+.).*Info[^{]+.([^}]+.)'
                           '.*Path[^\w]+([^"]+).*\$get[^\w]+([^"]+)'), post)
            form = {}
            form['__USERCONTROLPATH'] = urllib.unquote(urllib.unquote( \
                                        m.group(3)).decode('utf8')).decode('utf8')
            form['__SCRIPTMANAGERINFO'] = urllib.unquote(urllib.unquote("[{\"Name\":%s]" % \
                                          '},{"Name":'.join('"Value":'.join(m.group(2).split(':')) \
                                          .split(',')).replace('""', '","')).decode('utf8')).decode('utf8')
            form['__CONTROLCLIENTID'] = m.group(4)
            form['__PARAMETERS'] = m.group(1)
            form['__ENCRYPTED'] = 'true'
            forms.append(form)
        return forms

    @method
    class iter_accounts(TableElement):
        item_xpath = '//table//tr[td]'
        head_xpath = '//table//tr/th'

        col_id = u'Référence'
        col_label = u'Contrat'
        col_balance = u'Montant'

        class item(ItemElement):
            klass = Account

            load_details = Link(u'//td[2]/a') & AsyncLoad

            obj_id = CleanText(TableCell('id'))
            obj_label = CleanText(TableCell('label'))
            obj_balance = MyDecimal(TableCell('balance'))
            obj_type = Env('type')
            obj_iban = NotAvailable
            obj_valuation_diff = Async('details') & MyDecimal('//th[span[contains(text(), \
                                 "Performance")]]/following-sibling::td[1]')
            obj__page = Env('page')
            obj__acctype = "investment"

            def condition(self):
                return CleanText(TableCell('balance'))(self)

            def parse(self, el):
                page = Async('details').loaded_page(self)
                type = CleanText().filter(page.doc.xpath('//th[contains(text(), \
                        "Cadre fiscal")]/following-sibling::td[1]'))
                if not type:
                    raise SkipItem()
                self.env['type'] = self.page.TYPES.get(type.lower(), Account.TYPE_UNKNOWN)
                self.env['page'] = page

    @method
    class iter_investment(TableElement):
        item_xpath = '//div[@id="axaPopupdetailEpargne"]//table/tbody/tr[contains(@id, "ctl")]'
        head_xpath = '//div[@id="axaPopupdetailEpargne"]//table/thead/tr/th'

        col_label = re.compile('Support')
        col_code = 'Code ISIN'
        col_valuation = u'Montant de l\'épargne'
        col_quantity = u'Nombre d\'unités'
        col_unitvalue = u'Valeur Unité de Compte'
        col_portfolio_share = u'Répartition en %'
        col_vdate = u'Date de valeur'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_code = CleanText(TableCell('code'), default=NotAvailable)
            obj_quantity = MyDecimal(TableCell('quantity'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)
            obj_portfolio_share = Eval(lambda x: x / 100, MyDecimal(TableCell('portfolio_share')))

            def condition(self):
                return CleanText(TableCell('valuation'))(self)

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//div[@id="divMouvements"]//table/tbody/tr[position() < last()]'
        head_xpath = '//div[@id="divMouvements"]//table/thead/tr/th'

        col_date = 'Date'
        col_label = 'Nature'
        col_amount = re.compile('Montant')

        def next_page(self):
            link = Link('//a[@title="Page suivante" and @href]', default=None)(self)
            if link:
                form = self.page.get_form('//form')
                form['__EVENTTARGET'] = re.search('PostBackOptions[^\w]+([^"]+)', link).group(1)
                return requests.Request("POST", BrowserURL('investment', \
                       page=None)(self).replace('None', form.url), data=dict(form))

        class item(ItemElement):
            klass = InvestmentTransaction

            obj_raw = InvestmentTransaction.Raw(TableCell('label'))
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = MyDecimal(TableCell('amount'))


## Bank : done with browser 1


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
        # Browser is waiting for for 4 115,00 so we format the number to match this.
        if '.' in number and len(number.split('.')[-1]) == 2:
            return number.replace(',', ' ').replace('.', ',')
        return number


class BankAccountsPage(LoggedPage, MyHTMLPage):
    ACCOUNT_TYPES = OrderedDict((
        ('Visa',               Account.TYPE_CARD),
        ('courant-titre',      Account.TYPE_CHECKING),
        ('courant',            Account.TYPE_CHECKING),
        ('livret',             Account.TYPE_SAVINGS),
        ('Livret',             Account.TYPE_SAVINGS),
        ('LDD',                Account.TYPE_SAVINGS),
        ('PEA',                Account.TYPE_MARKET),
        ('Titres',             Account.TYPE_MARKET),
    ))

    def js2args(self, s):
        args = {}
        # For example:
        # noDoubleClic(this);;return oamSubmitForm('idPanorama','idPanorama:tableaux-comptes-courant-titre:0:tableaux-comptes-courant-titre-cartes:0:_idJsp321',null,[['paramCodeProduit','9'],['paramNumContrat','12234'],['paramNumCompte','12345678901'],['paramNumComptePassage','1234567890123456']]);
        for sub in re.findall("\['([^']+)','([^']+)'\]", s):
            args[sub[0]] = sub[1]

        args['idPanorama:_idcl'] = re.search("'(idPanorama:[^']+)'", s).group(1)
        args['idPanorama_SUBMIT'] = 1

        return args

    def get_list(self):
        for table in self.doc.getroot().cssselect('div#table-panorama table.table-produit'):
            tds = table.xpath('./tbody/tr')[0].findall('td')
            if len(tds) < 3:
                continue

            boxes = table.xpath('./tbody//tr')
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
                        account.id += args['idPanorama:_idcl'].split('Jsp')[-1]

                except KeyError:
                    account.id = args['paramNumCompte']

                for l in table.attrib['class'].split(' '):
                    if 'tableaux-comptes-' in l:
                        account_type_str =  l[len('tableaux-comptes-'):]
                        break
                else:
                    account_type_str = ''

                for pattern, type in self.ACCOUNT_TYPES.iteritems():
                    if pattern in account_type_str or pattern in account.label:
                        account.type = type
                        break
                else:
                    account.type = Account.TYPE_UNKNOWN

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
        error = CleanText(default="").filter(self.doc.xpath('//div[@id="titre_detail"]/h2'))
        return error if "Modifier votre code" in error else None

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

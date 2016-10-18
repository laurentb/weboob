# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from urllib import quote, urlencode
from decimal import Decimal
import re
from cStringIO import StringIO
from io import BytesIO
from datetime import date as da

from weboob.deprecated.browser import Page, BrokenPageError, BrowserIncorrectPassword
from weboob.exceptions import ActionNeeded
from weboob.tools.json import json
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import GridVirtKeyboard

class CDNVirtKeyboard(GridVirtKeyboard):
    symbols = {'0': '3de2346a63b658c977fce4da925ded28',
               '1': 'c571018d2dc267cdf72fafeeb9693037',
               '2': '72d7bad4beb833d85047f6912ed42b1d',
               '3': 'fbfce4677a8b2f31f3724143531079e3',
               '4': '54c723c5b0b5848a0475b4784100b9e0',
               '5': 'd00164307cacd4ca21b930db09403baa',
               '6': '101adc6f5d03df0f512c3ec2bef88de9',
               '7': '3b48f598209718397eb1118d81cf07ba',
               '8': '881f0acdaba2c44b6a5e64331f4f53d3',
               '9': 'a47d9a0a2ebbc65a0e625f20cb07822b',
              }

    margin = 1
    color = (0xff,0xf7,0xff)
    nrow = 4
    ncol = 4

    def __init__(self, browser, crypto, grid):
        f = BytesIO(browser.openurl('/sec/vk/gen_ui?modeClavier=0&cryptogramme=%s' % crypto).read())
        super(CDNVirtKeyboard, self).__init__(range(16), self.ncol, self.nrow, f, self.color)
        self.check_symbols(self.symbols, browser.responses_dirname)
        self.codes = grid

    def check_color(self, pixel):
        for p in pixel:
            if p > 0xd0:
                return False
        return True

    def get_string_code(self, string):
        res = []
        ndata = self.nrow * self.ncol
        for nbchar, c in enumerate(string):
            index = self.get_symbol_code(self.symbols[c])
            res.append(self.codes[(nbchar * ndata) + index])
        return ','.join(res)


class RedirectPage(Page):
    def on_loaded(self):
        for script in self.document.xpath('//script'):
            self.browser.location(re.search(r'href="([^"]+)"', script.text).group(1), no_login=True)

class LoginPage(Page):
    def login(self, username, password):
        login_selector = self.document.xpath('//input[@id="codsec"]')
        if login_selector:
            if not password.isdigit() or not len(password) == 6:
                raise BrowserIncorrectPassword('The credentials have changed on website %s. Please update them.' % self.browser.DOMAIN)
            self.vk_login(username, password)
        else:
            self.classic_login(username,password)

    def vk_login(self, username, password):
        res = self.browser.openurl('/sec/vk/gen_crypto?estSession=0').read()
        crypto = re.search(r"'crypto': '([^']+)'", res).group(1)
        grid = re.search(r"'grid': \[([^\]]+)]", res).group(1).split(',')

        vk = CDNVirtKeyboard(self.browser, crypto, grid)

        data = {'user_id':      username,
                'codsec':       vk.get_string_code(password),
                'cryptocvcs':   crypto,
                'vk_op':        'auth',
               }

        self.browser.location(self.browser.buildurl('/swm/redirectCDN.html'), urlencode(data), no_login=True)

    def classic_login(self, username, password):
        m = re.match('www.([^\.]+).fr', self.browser.DOMAIN)
        if not m:
            bank_name = 'credit-du-nord'
            self.logger.error('Unable to find bank name for %s' % self.browser.DOMAIN)
        else:
            bank_name = m.group(1)

        data = {'bank':         bank_name,
                'pagecible':    'vos-comptes',
                'password':     password.encode(self.browser.ENCODING),
                'pwAuth':       'Authentification+mot+de+passe',
                'username':     username.encode(self.browser.ENCODING),
               }

        self.browser.location(self.browser.buildurl('/saga/authentification'), urlencode(data), no_login=True)

class CDNBasePage(Page):
    def get_from_js(self, pattern, end, is_list=False):
        """
        find a pattern in any javascript text
        """
        value = None
        for script in self.document.xpath('//script'):
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

    def get_execution(self):
        return self.get_from_js("name: 'execution', value: '", "'")

    def iban_go(self):
        return '%s%s' % ('/vos-comptes/IPT/cdnProxyResource', self.get_from_js('C_PROXY.StaticResourceClientTranslation( "', '"'))


class AccountsPage(CDNBasePage):
    COL_HISTORY = 2
    COL_FIRE_EVENT = 3
    COL_ID = 4
    COL_LABEL = 5
    COL_BALANCE = -1

    TYPES = {u'CARTE':               Account.TYPE_CARD,
             u'COMPTE COURANT':      Account.TYPE_CHECKING,
             u'COMPTE EPARGNE':      Account.TYPE_SAVINGS,
             u'COMPTE SUR LIVRET':   Account.TYPE_SAVINGS,
             u'LIVRET':              Account.TYPE_SAVINGS,
             u'P.E.A.':              Account.TYPE_MARKET,
             u'PEA':                 Account.TYPE_MARKET,
             u'TITRES':              Account.TYPE_MARKET,
             u'ÉTOILE AVANCE':       Account.TYPE_LOAN,
            }

    def get_account_type(self, label):
        for pattern, actype in self.TYPES.iteritems():
            if label.startswith(pattern) or label.endswith(pattern):
                return actype

        return Account.TYPE_UNKNOWN

    def get_history_link(self):
        return self.parser.strip(self.get_from_js(",url: Ext.util.Format.htmlDecode('", "'"))

    def get_av_link(self):
        return self.document.xpath('//a[contains(text(), "Consultation")]')[0].attrib['href']

    def get_list(self):
        accounts = []

        txt = self.get_from_js('_data = new Array(', ');', is_list=True)

        if txt is None:
            raise BrokenPageError('Unable to find accounts list in scripts')

        data = json.loads('[%s]' % txt.replace("'", '"'))

        for line in data:
            a = Account()
            a.id = line[self.COL_ID].replace(' ', '')
            a._acc_nb = a.id.split('_')[0] if len(a.id.split('_')) > 1 else None
            fp = StringIO(unicode(line[self.COL_LABEL]).encode(self.browser.ENCODING))
            a.label = self.parser.tocleanstring(self.parser.parse(fp, self.browser.ENCODING).xpath('//div[@class="libelleCompteTDB"]')[0])
            # This account can be multiple life insurance accounts
            if a.label == 'ASSURANCE VIE-BON CAPI-SCPI-DIVERS *':
                continue

            a.balance = Decimal(FrenchTransaction.clean_amount(line[self.COL_BALANCE]))
            a.currency = a.get_currency(line[self.COL_BALANCE])
            a.type = self.get_account_type(a.label)
            if line[self.COL_HISTORY] == 'true':
                a._inv = False
                a._link = self.get_history_link()
                a._args = {'_eventId':         'clicDetailCompte',
                           '_ipc_eventValue':  '',
                           '_ipc_fireEvent':   '',
                           'deviseAffichee':   'DEVISE',
                           'execution':        self.get_execution(),
                           'idCompteClique':   line[self.COL_ID],
                          }
            else:
                a._inv = True
                a._args = {'_ipc_eventValue':  line[self.COL_ID],
                           '_ipc_fireEvent':   line[self.COL_FIRE_EVENT],
                          }
                a._link = self.document.xpath('//form[@name="changePageForm"]')[0].attrib['action']

            if a.type is Account.TYPE_CARD:
                a.coming = a.balance
                a.balance = Decimal('0.0')

            accounts.append(a)

        return accounts

    def iban_page(self):
        self.browser.select_form(name="changePageForm")
        self.browser.form.set_all_readonly(False)
        self.browser['_ipc_fireEvent'] = 'V1_rib'
        self.browser['_ipc_eventValue'] = 'bouchon=bouchon'
        self.browser.submit()


class AVPage(CDNBasePage):
    COL_LABEL = 0
    COL_BALANCE = 3

    ARGS = ['IndiceClassement', 'IndiceCompte', 'Banque', 'Agence', 'Classement', 'Serie', 'SScompte', 'Categorie', 'IndiceSupport', 'NumPolice', 'LinkHypertext']

    def get_params(self, text):
        url = self.get_from_js('document.detail.action="', '";')
        args = {}
        l = []
        for sub in re.findall("'([^']*)'", text):
            l.append(sub)
        for i, key in enumerate(self.ARGS):
            args[key] = unicode(l[self.ARGS.index(key)]).encode(self.browser.ENCODING)

        return url, args

    def get_av_accounts(self):
        for tr in self.document.xpath('//table[@class="datas"]/tr[not(@class)]'):
            cols = tr.findall('td')
            if len(cols) != 4:
                continue

            a = Account()
            a.label = self.parser.tocleanstring(cols[self.COL_LABEL])
            a.type = Account.TYPE_LIFE_INSURANCE
            a.balance = Decimal(FrenchTransaction.clean_amount(self.parser.tocleanstring(cols[self.COL_BALANCE])))
            a._link, a._args = self.get_params(cols[self.COL_LABEL].find('span/a').attrib['href'])
            a.id = '%s%s' % (a._args['IndiceSupport'], a._args['NumPolice'])
            a._acc_nb = None
            a._inv = True
            yield a


class ProAccountsPage(AccountsPage):
    COL_ID = 0
    COL_BALANCE = 1

    ARGS = ['Banque', 'Agence', 'Classement', 'Serie', 'SSCompte', 'Devise', 'CodeDeviseCCB', 'LibelleCompte', 'IntituleCompte', 'Indiceclassement', 'IndiceCompte', 'NomClassement']

    def params_from_js(self, text):
        l = []
        for sub in re.findall("'([^']*)'", text):
            l.append(sub)

        if len(l) <= 1:
             #For account that have no history
            return None, None

        kind = self.group_dict['kind']
        url = '/vos-comptes/IPT/appmanager/transac/' + kind + '?_nfpb=true&_windowLabel=portletInstance_18&_pageLabel=page_synthese_v1' + '&_cdnCltUrl=' + "/transacClippe/" + quote(l.pop(0))
        args = {}
        for input in self.document.xpath('//form[@name="detail"]/input'):
            args[input.attrib['name']] = input.attrib.get('value', '')

        for i, key in enumerate(self.ARGS):
            args[key] = unicode(l[self.ARGS.index(key)]).encode(self.browser.ENCODING)

        args['PageDemandee'] = 1
        args['PagePrecedente'] = 1

        return url, args

    def get_list(self):

        no_accounts_message = self.document.xpath(u'//span/b[contains(text(),"Votre abonnement est clôturé. Veuillez contacter votre conseiller.")]/text()')
        if no_accounts_message:
            raise ActionNeeded(no_accounts_message[0])

        for tr in self.document.xpath('//table[@class="datas"]//tr'):
            if tr.attrib.get('class', '') == 'entete':
                continue

            cols = tr.findall('td')

            a = Account()
            a.label = unicode(cols[self.COL_ID].xpath('.//span[@class="left-underline"]')[0].text.strip())
            a.type = self.get_account_type(a.label)
            balance = self.parser.tocleanstring(cols[self.COL_BALANCE])
            a.balance = Decimal(FrenchTransaction.clean_amount(balance))
            a.currency = a.get_currency(balance)
            a._link, a._args = self.params_from_js(cols[self.COL_ID].find('a').attrib['href'])
            a._acc_nb = cols[self.COL_ID].xpath('.//span[@class="right-underline"]')[0].text.replace(' ', '').strip()
            if a._args:
                a.id = '%s%s%s' % (a._acc_nb, a._args['IndiceCompte'], a._args['Indiceclassement'])
            else:
                a.id = a._acc_nb
            # This account can be multiple life insurance accounts
            if any(a.label.startswith(lab) for lab in ['ASS.VIE-BONS CAPI-SCPI-DIVERS', 'BONS CAPI-SCPI-DIVERS']) or \
               u'Aucun d\\351tail correspondant pour ce compte' in tr.xpath('.//a/@href')[0]:
                continue

            if a.type is Account.TYPE_CARD:
                a.coming = a.balance
                a.balance = Decimal('0.0')

            a._inv = False

            yield a

    def iban_page(self):
        self.browser.location(self.document.xpath('.//a[contains(text(), "Impression IBAN")]')[0].attrib['href'])


class IbanPage(Page):
    def get_iban(self):
        try:
            return unicode(self.document.xpath('.//td[@width="315"]/font')[0].text.replace(' ', '').strip())
        except AttributeError:
            return NotAvailable


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>RET DAB \w+ .*?) LE (?P<dd>\d{2})(?P<mm>\d{2})$'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^VIR(EMENT)?( INTERNET)?(\.| )?(DE)? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^PRLV (SEPA )?(DE )?(?P<text>.*?)( Motif :.*)?$'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^CB (?P<text>.*) LE (?P<dd>\d{2})\.?(?P<mm>\d{2})$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^CHEQUE.*'),                  FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(CONVENTION \d+ )?COTISATION (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile(r'^REM(ISE)?\.?( CHQ\.)? .*'),  FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^(?P<text>.*?)( \d{2}.*)? LE (?P<dd>\d{2})\.?(?P<mm>\d{2})$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<text>.*?) LE (?P<dd>\d{2}) (?P<mm>\d{2}) (?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_CARD),
               ]


class TransactionsPage(CDNBasePage):
    COL_ID = 0
    COL_DATE = -5
    COL_DEBIT_DATE = -4
    COL_LABEL = -3
    COL_VALUE = -1

    def get_next_args(self, args):
        if self.is_last():
            return None

        args['_eventId'] = 'clicChangerPageSuivant'
        args['execution'] = self.get_execution()
        args.pop('idCompteClique', None)
        return args

    def is_last(self):
        for script in self.document.xpath('//script'):
            txt = script.text
            if txt is None:
                continue

            if txt.find('clicChangerPageSuivant') >= 0:
                return False

        return True

    def condition(self, t, acc_type):
        if t.date is NotAvailable:
            return True

        t._is_coming = t.date > da.today()

        if t.raw.startswith('TOTAL DES') or t.raw.startswith('ACHATS CARTE'):
            t.type = t.TYPE_CARD_SUMMARY
        elif acc_type is Account.TYPE_CARD:
            t.type = t.TYPE_DEFERRED_CARD
        return False

    def get_history(self, acc_type):
        txt = self.get_from_js('ListeMvts_data = new Array(', ');\n')

        if txt is None:
            no_trans = self.get_from_js('js_noMvts = new Ext.Panel(', ')')
            if no_trans is not None:
                # there is no transactions for this account, this is normal.
                return
            else:
                # No history on this account
                return

        data = json.loads('[%s]' % txt.replace('"', '\\"').replace("'", '"'))

        for line in data:
            t = Transaction()

            if acc_type is Account.TYPE_CARD:
                date = vdate = self.parser.strip(line[self.COL_DEBIT_DATE])
            else:
                date = self.parser.strip(line[self.COL_DATE])
                vdate = self.parser.strip(line[self.COL_DEBIT_DATE])
            raw = self.parser.strip(line[self.COL_LABEL])

            t.parse(date, raw, vdate=vdate)
            t.set_amount(line[self.COL_VALUE])

            if self.condition(t, acc_type):
                continue

            yield t

    def get_market_investment(self):
        COL_LABEL = 0
        COL_QUANTITY = 1
        COL_UNITPRICE = 2
        COL_UNITVALUE = 3
        COL_VALUATION = 4
        COL_PERF = 5
        for table in self.document.xpath('//table[@class="datas-large"]'):
            for tr in table.xpath('.//tr[not(@class="entete")]'):
                cols = tr.findall('td')
                if len(cols) < 7:
                    continue
                delta = 0
                if len(cols) == 9:
                    delta = 1

                inv = Investment()
                inv.code = self.parser.tocleanstring(cols[COL_LABEL + delta].xpath('.//span')[1]).split(' ')[0].split(u'\xa0')[0]
                inv.label = self.parser.tocleanstring(cols[COL_LABEL + delta].xpath('.//span')[0])
                inv.quantity = self.parse_decimal(cols[COL_QUANTITY + delta])
                inv.unitprice = self.parse_decimal(cols[COL_UNITPRICE + delta])
                inv.unitvalue = self.parse_decimal(cols[COL_UNITVALUE + delta])
                inv.valuation = self.parse_decimal(cols[COL_VALUATION + delta])
                inv.diff = self.parse_decimal(cols[COL_PERF + delta])

                yield inv

    def get_deposit_investment(self):
        COL_LABEL = 0
        COL_QUANTITY = 3
        COL_UNITVALUE = 4
        COL_VALUATION = 5
        for tr in self.document.xpath('//table[@class="datas"]/tr[not(@class="entete")]'):
            cols = tr.findall('td')

            inv = Investment()
            inv.label = self.parser.tocleanstring(cols[COL_LABEL].xpath('.//a')[0])
            inv.code = self.parser.tocleanstring(cols[COL_LABEL]).replace(inv.label, "").split(' ')[0].split(u'\xa0')[0]
            inv.quantity = self.parse_decimal(cols[COL_QUANTITY])
            inv.unitvalue = self.parse_decimal(cols[COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols[COL_VALUATION])

            yield inv

    def parse_decimal(self, string):
        value = self.parser.tocleanstring(string)
        if value == '-':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))

    def fill_valuation_diff(self, account):
        account.valuation_diff = self.parse_decimal(self.document.xpath(u'//td[span[contains(text(), "dont +/- value : ")]]//b')[0])

class ProTransactionsPage(TransactionsPage):
    def get_next_args(self, args):
        if len(self.document.xpath('//a[contains(text(), "Suivant")]')) > 0:
            args['PageDemandee'] = int(args.get('PageDemandee', 1)) + 1
            return args

        return None

    def parse_transactions(self):
        transactions = {}
        for script in self.document.xpath('//script'):
            txt = script.text
            if txt is None:
                continue

            for i, key, value in re.findall('listeopecv\[(\d+)\]\[\'(\w+)\'\]="(.*)";', txt):
                i = int(i)
                if i not in transactions:
                    transactions[i] = {}
                transactions[i][key] = value

        return transactions.iteritems()

    def get_history(self, acc_type):
        for i, tr in self.parse_transactions():
            t = Transaction()
            if acc_type is Account.TYPE_CARD:
                date = vdate = tr['dateval']
            else:
                date = tr['date']
                vdate = tr['dateval'] or date
            raw = self.parser.strip('<p>%s</p>' % (' '.join([tr['typeope'], tr['LibComp']])))
            t.parse(date, raw, vdate)
            t.set_amount(tr['mont'])

            if self.condition(t, acc_type):
                continue

            yield t

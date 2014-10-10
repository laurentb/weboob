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


from urllib import quote
from decimal import Decimal
import re
from cStringIO import StringIO

from weboob.deprecated.browser import Page, BrokenPageError
from weboob.tools.json import json
from weboob.capabilities.bank import Account
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(Page):
    pass


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


class AccountsPage(CDNBasePage):
    COL_HISTORY = 2
    COL_ID = 4
    COL_LABEL = 5
    COL_BALANCE = -1

    TYPES = {'ASSURANCE VIE':       Account.TYPE_DEPOSIT,
             'CARTE':               Account.TYPE_CARD,
             'COMPTE COURANT':      Account.TYPE_CHECKING,
             'COMPTE EPARGNE':      Account.TYPE_SAVINGS,
             'COMPTE SUR LIVRET':   Account.TYPE_SAVINGS,
             'LIVRET':              Account.TYPE_SAVINGS,
             'P.E.A.':              Account.TYPE_MARKET,
             'PEA':                 Account.TYPE_MARKET,
            }

    def get_account_type(self, label):
        for pattern, actype in self.TYPES.iteritems():
            if label.startswith(pattern):
                return actype

        return Account.TYPE_UNKNOWN

    def get_history_link(self):
        return self.parser.strip(self.get_from_js(",url: Ext.util.Format.htmlDecode('", "'"))

    def get_list(self):
        accounts = []

        txt = self.get_from_js('_data = new Array(', ');', is_list=True)

        if txt is None:
            raise BrokenPageError('Unable to find accounts list in scripts')

        data = json.loads('[%s]' % txt.replace("'", '"'))

        for line in data:
            a = Account()
            a.id = line[self.COL_ID].replace(' ', '')
            fp = StringIO(unicode(line[self.COL_LABEL]).encode(self.browser.ENCODING))
            a.label = self.parser.tocleanstring(self.parser.parse(fp, self.browser.ENCODING).xpath('//div[@class="libelleCompteTDB"]')[0])
            a.balance = Decimal(FrenchTransaction.clean_amount(line[self.COL_BALANCE]))
            a.currency = a.get_currency(line[self.COL_BALANCE])
            a.type = self.get_account_type(a.label)
            a._link = self.get_history_link()
            if line[self.COL_HISTORY] == 'true':
                a._args = {'_eventId':         'clicDetailCompte',
                           '_ipc_eventValue':  '',
                           '_ipc_fireEvent':   '',
                           'deviseAffichee':   'DEVISE',
                           'execution':        self.get_execution(),
                           'idCompteClique':   line[self.COL_ID],
                          }
            else:
                a._args = None

            if a.id.find('_CarteVisa') >= 0:
                accounts[-1]._card_ids.append(a._args)
                if not accounts[-1].coming:
                    accounts[-1].coming = Decimal('0.0')
                accounts[-1].coming += a.balance
                continue

            a._card_ids = []
            accounts.append(a)

        return iter(accounts)


class ProAccountsPage(AccountsPage):
    COL_ID = 0
    COL_BALANCE = 1

    ARGS = ['Banque', 'Agence', 'Classement', 'Serie', 'SSCompte', 'Devise', 'CodeDeviseCCB', 'LibelleCompte', 'IntituleCompte', 'Indiceclassement', 'IndiceCompte', 'NomClassement']

    def params_from_js(self, text):
        l = []
        for sub in re.findall("'([^']*)'", text):
            l.append(sub)

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
        for tr in self.document.xpath('//table[@class="datas"]//tr'):
            if tr.attrib.get('class', '') == 'entete':
                continue

            cols = tr.findall('td')

            a = Account()
            a.id = cols[self.COL_ID].xpath('.//span[@class="right-underline"]')[0].text.strip()
            a.label = unicode(cols[self.COL_ID].xpath('.//span[@class="left-underline"]')[0].text.strip())
            a.type = self.get_account_type(a.label)
            balance = self.parser.tocleanstring(cols[self.COL_BALANCE])
            a.balance = Decimal(FrenchTransaction.clean_amount(balance))
            a.currency = a.get_currency(balance)
            a._link, a._args = self.params_from_js(cols[self.COL_ID].find('a').attrib['href'])

            a._card_ids = []

            yield a


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
               ]


class TransactionsPage(CDNBasePage):
    COL_ID = 0
    COL_DATE = 1
    COL_DEBIT_DATE = 2
    COL_LABEL = 3
    COL_VALUE = -1

    is_coming = None

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

    def set_coming(self, t):
        if self.is_coming is not None and t.raw.startswith('TOTAL DES') and t.amount > 0:
            # ignore card credit and next transactions are already debited
            self.is_coming = False
            return True
        if self.is_coming is None and t.raw.startswith('ACHATS CARTE'):
            # Ignore card debit
            return True

        t._is_coming = bool(self.is_coming)
        return False

    def get_history(self):
        txt = self.get_from_js('ListeMvts_data = new Array(', ');')

        if txt is None:
            no_trans = self.get_from_js('js_noMvts = new Ext.Panel(', ')')
            if no_trans is not None:
                # there is no transactions for this account, this is normal.
                return
            else:
                raise BrokenPageError('Unable to find transactions list in scripts')

        data = json.loads('[%s]' % txt.replace('"', '\\"').replace("'", '"'))

        for line in data:
            t = Transaction(line[self.COL_ID])

            if self.is_coming is not None:
                t.type = t.TYPE_CARD
                date = self.parser.strip(line[self.COL_DEBIT_DATE])
            else:
                date = self.parser.strip(line[self.COL_DATE])
            raw = self.parser.strip(line[self.COL_LABEL])

            t.parse(date, raw)
            t.set_amount(line[self.COL_VALUE])

            if t.date is NotAvailable:
                continue

            if self.set_coming(t):
                continue

            yield t


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

    def get_history(self):
        for i, tr in self.parse_transactions():
            t = Transaction(i)
            date = tr['date']
            raw = self.parser.strip('<p>%s</p>' % (' '.join([tr['typeope'], tr['LibComp']])))
            t.parse(date, raw)
            t.set_amount(tr['mont'])

            if self.set_coming(t):
                continue

            yield t

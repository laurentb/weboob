# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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


from decimal import Decimal
import re

from weboob.tools.json import json
from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(Page):
    def login(self, login, password):
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'AuthForm')
        self.browser['j_username'] = login.encode('iso-8859-15')
        self.browser['j_password'] = password.encode('iso-8859-15')
        self.browser.submit(nologin=True)


class LoggedPage(Page):
    def get_error(self):
        div = self.document.xpath('//div[@class="errorForm-msg"]')
        if len(div) == 0:
            return None

        msg = u', '.join([li.text.strip() for li in div[0].xpath('.//li')])
        return re.sub('[\r\n\t\xa0]+', ' ', msg)


class AccountsPage(Page):
    ACCOUNT_TYPES = {u'COMPTE NEF': Account.TYPE_CHECKING}

    def get_list(self):
        for table in self.document.getroot().cssselect('table.table-synthese'):
            account = Account()
            labels = table.xpath('.//ul[@class="nClient"]/li')
            account_type_str = table.xpath('.//h2[@class="tt_compte"]')[0].text.strip()

            account.id = re.sub(u'[^0-9]', '', labels[-1].text)
            account.label = u' '.join([account_type_str, labels[0].text.strip()])
            account.type = self.ACCOUNT_TYPES.get(account_type_str, Account.TYPE_UNKNOWN)

            balance = table.xpath('.//td[@class="sum_solde"]//span')[-1].text
            account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            account.currency = account.get_currency(balance)

            yield account


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(?P<text>RETRAIT DAB) (?P<dd>\d{2})-(?P<mm>\d{2})-([\d\-]+)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})-(?P<mm>\d{2})-([\d\-]+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CARTE (?P<dd>\d{2})(?P<mm>\d{2}) \d+ (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^VIR COOPA (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^VIR(EMENT|EMT| SEPA EMET :)? (?P<text>.*?)(- .*)?$'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(PRLV|PRELEVEMENT) (?P<text>.*?)(- .*)?$'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*'),                   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'),FrenchTransaction.TYPE_BANK),
                (re.compile('^ABONNEMENT (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(Page):
    pass


class TransactionsJSONPage(Page):
    ROW_DATE =    0
    ROW_TEXT =    2
    ROW_CREDIT = -1
    ROW_DEBIT =  -2

    def get_transactions(self):
        seen = set()
        for tr in self.document['exportData'][1:]:
            t = Transaction(0)
            t.parse(tr[self.ROW_DATE], tr[self.ROW_TEXT])
            t.set_amount(tr[self.ROW_CREDIT], tr[self.ROW_DEBIT])
            t.id = t.unique_id(seen)
            yield t


class ComingTransactionsPage(Page):
    ROW_REF =     0
    ROW_TEXT =    1
    ROW_DATE =    2
    ROW_CREDIT = -1
    ROW_DEBIT =  -2

    def get_transactions(self):
        data = []
        for script in self.document.xpath('//script'):
            txt = script.text
            if txt is None:
                continue

            pattern = 'var jsonData ='
            start = txt.find(pattern)
            if start < 0:
                continue

            txt = txt[start+len(pattern):start+txt[start:].find(';')]
            data = json.loads(txt)
            break

        for tr in data:
            t = Transaction(0)
            t.parse(tr[self.ROW_DATE], tr[self.ROW_TEXT])
            t.set_amount(tr[self.ROW_CREDIT], tr[self.ROW_DEBIT])
            yield t

# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.deprecated.browser import Page
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date


class LoginPage(Page):
    def login(self, login, password):
        self.browser.select_form(name='login_form')
        self.browser['login_email'] = login.encode(self.browser.ENCODING)
        self.browser['login_password'] = password.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)


class UselessPage(Page):
    pass


class HomePage(Page):
    pass


class AccountPage(Page):
    def get_account(self, _id):
        return self.get_accounts().get(_id)

    def get_accounts(self):
        accounts = {}
        content = self.document.xpath('//div[@id="moneyPage"]')[0]

        # Primary currency account
        primary_account = Account()
        primary_account.type = Account.TYPE_CHECKING
        try:
            balance = self.parser.tocleanstring(content.xpath('//div[contains(@class, "col-md-6")][contains(@class, "available")]')[0])
        except IndexError:
            primary_account.id = 'EUR'
            primary_account.currency = 'EUR'
            primary_account.balance = NotAvailable
            primary_account.label = u'%s' % (self.browser.username)
        else:
            primary_account.currency = Account.get_currency(balance)
            primary_account.id = unicode(primary_account.currency)
            primary_account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            primary_account.label = u'%s %s*' % (self.browser.username, primary_account.currency)

        accounts[primary_account.id] = primary_account

        return accounts


class ProHistoryPage(Page):
    def iter_transactions(self, account):
        for trans in self.parse():
            if trans._currency == account.currency:
                yield trans

    def parse(self):
        for tr in self.document.xpath('//tr'):
            t = FrenchTransaction(tr.xpath('./td[@class="transactionId"]/span')[0].text.strip())
            date = parse_french_date(tr.xpath('./td[@class="date"]')[0].text.strip())
            status = tr.xpath('./td[@class="desc"]/ul/li[@class="first"]')[0].text.strip()
            #We pass this because it's not transaction
            if status in [u'Créé', u'Annulé', u'Suspendu', u'Mis à jour']:
                continue
            raw = tr.xpath('./td[@class="desc"]/strong')[0].text.strip()
            t.parse(date=date, raw=raw)
            amount = tr.xpath('./td[@class="price"]/span')[0].text.strip()
            t.set_amount(amount)
            t._currency = Account.get_currency(amount)
            yield t

    def transaction_left(self):
        return len(self.document.xpath('//div[@class="no-records"]')) == 0


class PartHistoryPage(Page):
    def transaction_left(self):
        return len(self.document['data']['activity']['COMPLETED']) > 0 or len(self.document['data']['activity']['PENDING']) > 0

    def iter_transactions(self, account):
        for trans in self.parse(account):
            yield trans

    def parse(self, account):
        transactions = list()

        for status in ['PENDING', 'COMPLETED']:
            transac = self.document['data']['activity'][status]
            for t in transac:
                tran = self.parse_transaction(t, account)
                if tran:
                    transactions.append(tran)

        transactions.sort(key=lambda tr: tr.rdate, reverse=True)
        for t in transactions:
            yield t

    def parse_transaction(self, transaction, account):
        t = FrenchTransaction(transaction['activityId'])
        date = parse_french_date(transaction['date'])
        raw = transaction.get('counterparty', transaction['displayType'])
        t.parse(date=date, raw=raw)

        try:
            if transaction['currencyCode'] != account.currency:
                transaction = self.browser.convert_amount(account, transaction)
                t.original_amount = self.format_amount(transaction['originalAmount'], transaction["isCredit"])
                t.original_currency = transaction["currencyCode"]
            t.amount = self.format_amount(transaction['netAmount'], transaction["isCredit"])
        except KeyError:
            return

        t._currency = transaction['currencyCode']

        return t

    def format_amount(self, to_format, is_credit):
        m = re.search(r"\D", to_format[::-1])
        amount = Decimal(re.sub(r'[^\d]', '', to_format))/Decimal((10 ** m.start()))
        if is_credit:
            return abs(amount)
        else:
            return -abs(amount)

class HistoryDetailsPage(Page):
    def get_converted_amount(self, account):
        find_td = self.document.xpath('//td[contains(text(),"' + account.currency + ')")]')
        if len(find_td) > 0 :
            convert_td = find_td[0].text
            m = re.match('.* ([^ ]+) ' + account.currency + '\).*', convert_td)
            if m:
                return m.group(1)
        return False

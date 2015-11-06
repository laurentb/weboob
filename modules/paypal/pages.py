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
from weboob.exceptions import BrowserUnavailable
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.filters.standard import CleanText
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date
from weboob.tools.js import Javascript



class PromoPage(LoggedPage, HTMLPage):
    def on_load(self):
        # We land sometimes on this page, it's better to raise an unavailable browser
        # than an Incorrect Password
        raise BrowserUnavailable('Promo Page')

class LoginPage(HTMLPage):
    def get_token_and_csrf(self, code):
        code1 = re.search('(function .*)\(function\(\)', code).group(1)
        # now it checks if some browsers-only builtin variables are defined:
        # e+=function(e,t){return typeof navigator!="undefined"?e:t}
        js = Javascript('var navigator = {}; ' + code1)
        func_name = re.search(r'function (\w+)\(\)', code1).group(1)
        token = str(js.call(func_name))
        csrf = re.search(r'csrf="\+encodeURIComponent\("(.*?)"\)', code).group(1)
        return token, csrf

    def login(self, login, password):
        #Paypal use this to check if we accept cookie
        self.browser.session.cookies.set('cookie_check', 'yes')

        form = self.get_form(name='login')
        form['login_email'] = login
        form['login_password'] = password
        return form.submit(headers={'X-Requested-With': 'XMLHttpRequest'})

    def get_script_url(self):
        list1 = self.doc.xpath('//script')
        for s in list1:
            if 'src' in s.attrib and 'challenge' in s.attrib['src']:
                return s.attrib['src']

class ErrorPage(HTMLPage):
    pass

class UselessPage(LoggedPage, HTMLPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    pass


class AccountPage(LoggedPage, HTMLPage):
    def get_account(self, _id):
        return self.get_accounts().get(_id)

    def get_accounts(self):
        accounts = {}
        content = self.doc.xpath('//div[@id="moneyPage"]')[0]

        # Primary currency account
        primary_account = Account()
        primary_account.type = Account.TYPE_CHECKING
        try:
            balance = CleanText('.')(content.xpath('//div[contains(@class, "col-md-6")][contains(@class, "available")]')[0])
        except IndexError:
            primary_account.id = 'EUR'
            primary_account.currency = u'EUR'
            primary_account.balance = NotAvailable
            primary_account.label = u'%s' % (self.browser.username)
        else:
            primary_account.currency = Account.get_currency(balance)
            primary_account.id = unicode(primary_account.currency)
            primary_account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            primary_account.label = u'%s %s*' % (self.browser.username, primary_account.currency)

        accounts[primary_account.id] = primary_account

        return accounts


class HistoryPage(LoggedPage):
    def iter_transactions(self, account):
        for trans in self.parse(account):
            yield trans

    def parse(self, account):
        transactions = list()

        transacs = self.get_transactions()

        for t in transacs:
            tran = self.parse_transaction(t, account)
            if tran:
                transactions.append(tran)

        for t in transactions:
            yield t

    def format_amount(self, to_format, is_credit):
        m = re.search(r"\D", to_format[::-1])
        amount = Decimal(re.sub(r'[^\d]', '', to_format))/Decimal((10 ** m.start()))
        if is_credit:
            return abs(amount)
        else:
            return -abs(amount)

class ProHistoryPage(HistoryPage, JsonPage):
    def transaction_left(self):
        return len(self.doc['data']['transactions']) > 0

    def get_transactions(self):
        return self.doc['data']['transactions']

    def parse_transaction(self, transaction, account):
        if transaction['transactionStatus'] in [u'Créé', u'Annulé', u'Suspendu', u'Mis à jour', u'Actif', u'Payé', u'En attente', u'Rejeté']:
            return
        if transaction['transactionDescription'].startswith('Offre de remboursement'):
            return
        t = FrenchTransaction(transaction['transactionId'])
        if not transaction['transactionAmount']['currencyCode'] == account.currency:
            cc = self.browser.convert_amount(account, transaction, 'https://www.paypal.com/cgi-bin/webscr?cmd=_history-details-from-hub&id=' + transaction['transactionId'])
            if not cc:
                return
            t.original_amount = Decimal('%.2f' % transaction['transactionAmount']['currencyDoubleValue'])
            t.original_currency = u'' + transaction['transactionAmount']['currencyCode']
            t.set_amount(cc)
        else:
            t.amount = Decimal('%.2f' % transaction['net']['currencyDoubleValue'])
        date = parse_french_date(transaction['transactionTime'])
        raw = transaction['transactionDescription']
        t.commission = Decimal('%.2f' % transaction['fee']['currencyDoubleValue'])
        t.parse(date=date, raw=raw)
        return t


class PartHistoryPage(HistoryPage, JsonPage):
    def transaction_left(self):
        return self.doc['data']['activity']['hasTransactionsCompleted'] or self.doc['data']['activity']['hasTransactionsPending']

    def get_transactions(self):
            return self.doc['data']['activity']['transactions']

    def parse_transaction(self, transaction, account):
        t = FrenchTransaction(transaction['id'])
        if not transaction['isPrimaryCurrency']:
            cc = self.browser.convert_amount(account, transaction, transaction['detailsLink'])
            if not cc:
                return
            t.original_amount = self.format_amount(transaction['amounts']['net']['value'], transaction["isCredit"])
            t.original_currency = u'' + transaction['amounts']['txnCurrency']
            t.amount = self.format_amount(cc, transaction['isCredit'])
        else:
            t.amount = self.format_amount(transaction['amounts']['net']['value'], transaction['isCredit'])
        date = parse_french_date(transaction['date']['formattedDate'] + ' ' + transaction['date']['year'])
        raw = transaction.get('counterparty', transaction['displayType'])
        t.parse(date=date, raw=raw)

        return t

class HistoryDetailsPage(LoggedPage, HTMLPage):
    def get_converted_amount(self, account):
        find_td = self.doc.xpath('//td[contains(text(),"' + account.currency + ')")]')
        if len(find_td) > 0 :
            convert_td = find_td[0].text
            m = re.match('.* ([^ ]+) ' + account.currency + '\).*', convert_td)
            if m:
                return m.group(1)
        return False

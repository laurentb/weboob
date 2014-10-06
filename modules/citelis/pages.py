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
import datetime
import re

from weboob.deprecated.browser import Page, BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    @classmethod
    def clean_amount(cls, text):
        text = text.strip()
        # Convert "American" UUU.CC format to "French" UUU,CC format
        if re.search(r'\d\.\d\d$', text):
            text = text.replace(',', ' ').replace('.', ',')
        return FrenchTransaction.clean_amount(text)


class LoginPage(Page):
    def login(self, merchant_id, login, password):
        self.browser.select_form(name='loginForm')
        self.browser['merchant'] = merchant_id.encode(self.browser.ENCODING)
        self.browser['login'] = login.encode(self.browser.ENCODING)
        self.browser['password'] = password.encode(self.browser.ENCODING)
        self.browser.submit()


class SummaryPage(Page):
    def clean_amount(self, el, debit):
        amount = Decimal(Transaction.clean_amount(el.text_content()))
        if amount == Decimal('0.00'):
            return None
        if debit and amount > Decimal('0'):
            return -1 * amount
        return amount

    def get_balance(self):
        zone = self.parser.select(self.document.getroot(), '#ActionZone_Euro', 1)
        for tr in self.parser.select(zone, '#transactionError tr'):
            tds = self.parser.select(tr, 'td')
            if tds and tds[0].text_content().strip() == 'Total':
                debit, credit = self.parser.select(tr, 'td.amount', 4)[-2:]  # keep the last 2
                debit = self.clean_amount(debit, debit=True)
                credit = self.clean_amount(credit, debit=False)
                amount = credit or debit
                return amount


class UselessPage(Page):
    def on_loaded(self):
        for error in self.document.xpath('//li[@class="error"]'):
            raise BrowserIncorrectPassword(self.parser.tocleanstring(error))


class TransactionSearchPage(Page):
    def search(self, accepted=True, refused=False):
        self.browser.select_form(name='transactionSearchForm')
        self.browser['selectedDateCriteria'] = ['thisweek']  # TODO ask for more
        self.browser['transactionAccepted'] = ['0'] if accepted else []
        self.browser['transactionRefused'] = ['0'] if refused else []

        # simulate the javascript
        nonce = self.parser.select(self.document.getroot(), '#menu li.global a')[0] \
            .attrib['href'].partition('CSRF_NONCE=')[2]
        self.browser.form.action = '%s://%s/transactionSearch.do?reqCode=%s&org.apache.catalina.filters.CSRF_NONCE=%s&screen=new' % (self.browser.PROTOCOL, self.browser.DOMAIN, 'search', nonce)
        self.browser.submit()


class TransactionsPage(Page):
    def get_csv_url(self):
        for a in self.parser.select(self.document.getroot(), '.exportlinks a'):
            if len(self.parser.select(a, 'span.csv')):
                return a.attrib['href']


class TransactionsCsvPage(Page):
    def guess_format(self, amount):
        if re.search(r'\d\.\d\d$', amount):
            date_format = "%m/%d/%Y"
        else:
            date_format = "%d/%m/%Y"
        time_format = "%H:%M:%S"
        return date_format + ' ' + time_format

    def iter_transactions(self):
        ID = 0
        DATE = 2
        AMOUNT = 4
        CARD = 7
        NUMBER = 8
        for row in self.document.rows:
            t = Transaction(row[ID])
            date = row[DATE]
            amount = row[AMOUNT]
            datetime_format = self.guess_format(amount)
            t.set_amount(amount)
            t.parse(datetime.datetime.strptime(date, datetime_format),
                    row[CARD] + '  ' + row[NUMBER])
            yield t

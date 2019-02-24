# -*- coding: utf-8 -*-

# Copyright(C) 2015 Cédric Félizard
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import datetime
import re
from decimal import Decimal
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import AmericanTransaction as EnglishTransaction


__all__ = ['LoginPage', 'AccountPage', 'HistoryPage']


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='aspnetForm')
        form['ctl00$chi$txtUserName'] = username
        form['ctl00$chi$txtPassword'] = password
        form.submit()


class AccountPage(LoggedPage, HTMLPage):
    def get_accounts(self):
        for el in self.doc.getroot().cssselect('div#content tr.row'):
            account = Account()

            balance = el.cssselect('td.Balance')[0].text
            account.balance = Decimal(Transaction.clean_amount(balance))
            account.id = el.cssselect('span')[0].text.strip()
            account.currency = u'NZD'  # TODO: handle other currencies
            account.type = Account.TYPE_CHECKING

            if el.cssselect('td.AccountName > a'):
                label_el = el.cssselect('td.AccountName > a')[0]
                account._link = label_el.get('href')
            else:
                label_el = el.cssselect('td.AccountName')[0]
                account._link = None

            account.label = unicode(label_el.text.strip())

            yield account


class HistoryPage(LoggedPage, HTMLPage):
    def get_history(self):
        # TODO: get more results from "next" page, only 15 transactions per page
        for el in self.doc.getroot().cssselect('div#content tr.row'):
            transaction = Transaction()

            label = unicode(el.cssselect('td.tranDesc')[0].text)
            transaction.label = label

            for pattern, _type in Transaction.PATTERNS:
                match = pattern.match(label)
                if match:
                    transaction.type = _type
                    break

            date = el.cssselect('td.tranDate')[0].text
            transaction.date = datetime.datetime.strptime(date, '%d %b \'%y')

            amount = el.cssselect('td.tranAmnt')[0].text
            transaction.amount = Decimal(Transaction.clean_amount(amount))

            yield transaction


class Transaction(EnglishTransaction):
    PATTERNS = [
        (re.compile(r'^POS W/D (?P<text>.*)'), EnglishTransaction.TYPE_CARD),
        (re.compile(r'^ATM W/D (?P<text>.*)'), EnglishTransaction.TYPE_WITHDRAWAL),
        (re.compile(r'^(PAY|FROM) (?P<text>.*)'), EnglishTransaction.TYPE_TRANSFER),
    ]

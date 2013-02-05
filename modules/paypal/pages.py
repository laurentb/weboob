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
import datetime

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.parsers.csvparser import CsvParser
from weboob.capabilities.bank import Account, Transaction
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['LoginPage', 'AccountPage']


def clean_amount(text):
    """
    >>> clean_amount('42')
    Decimal('42')
    >>> clean_amount('42,12')
    Decimal('42.12')
    >>> clean_amount('42.12')
    Decimal('42.12')
    >>> clean_amount('$42.12 USD')
    Decimal('42.12')
    >>> clean_amount('$12.442,12 USD')
    Decimal('12442.12')
    >>> clean_amount('$12,442.12 USD')
    Decimal('12442.12')
    """
    # Convert "American" UUU.CC format to "French" UUU,CC format
    if re.search(r'\d\.\d\d(?: [A-Z]+)?$', text):
        text = text.replace(',', ' ').replace('.', ',')
    return Decimal(FrenchTransaction.clean_amount(text))


class LoginPage(BasePage):
    def login(self, login, password):
        self.browser.select_form(name='login_form')
        self.browser['login_email'] = login
        self.browser['login_password'] = password
        self.browser.submit(nologin=True)


class AccountPage(BasePage):
    def get_account(self, _id):
        return self.get_accounts().get(_id)

    def get_accounts(self):
        accounts = {}
        content = self.document.xpath('//div[@id="main"]//div[@class="col first"]')[0]

        # Total currency balance.
        # If there are multiple currencies, this balance is all currencies
        # converted to the main currency.
        balance = content.xpath('.//h3/span[@class="balance"]')
        if not balance:
            balance = content.xpath('.//li[@class="balance"]//span/strong')
        balance = balance[0].text_content().strip()

        # Primary currency account
        primary_account = Account()
        primary_account.type = Account.TYPE_CHECKING
        primary_account.balance = clean_amount(balance)
        primary_account.currency = Account.get_currency(balance)
        primary_account.id = unicode(primary_account.currency)
        primary_account.label = u'%s %s*' % (self.browser.username, balance.split()[-1])
        accounts[primary_account.id] = primary_account

        # The following code will only work if the user enabled multiple currencies.
        balance = content.xpath('.//div[@class="body"]//ul/li[@class="balance"]/span')
        table = content.xpath('.//table[@id="balanceDetails"]//tbody//tr')

        # sanity check
        if bool(balance) is not bool(table):
            raise BrokenPageError('Unable to find all required multiple currency entries')

        # Primary currency balance.
        # If the user enabled multiple currencies, we get this one instead.
        # An Account object has only one currency; secondary currencies should be other accounts.
        if balance:
            balance = balance[0].text_content().strip()
            primary_account.balance = clean_amount(balance)
            # The primary currency of the "head balance" is the same; ensure we got the right one
            assert primary_account.currency == primary_account.get_currency(balance)

        for row in table:
            balance = row.xpath('.//td')[-1].text_content().strip()
            account = Account()
            account.type = Account.TYPE_CHECKING
            account.balance = clean_amount(balance)
            account.currency = Account.get_currency(balance)
            account.id = unicode(account.currency)
            account.label = u'%s %s' % (self.browser.username, balance.split()[-1])
            if account.id == primary_account.id:
                assert account.balance == primary_account.balance
                assert account.currency == primary_account.currency
            elif account.currency:
                accounts[account.id] = account

        return accounts


class DownloadHistoryPage(BasePage):
    def download(self):
        today = datetime.date.today()
        self.browser.select_form(name='form1')
        # download an entire year
        self.browser['to_c'] = str(today.year)
        self.browser['to_a'] = str(today.month)
        self.browser['to_b'] = str(today.day)
        self.browser['from_c'] = str(today.year - 1)
        self.browser['from_a'] = str(today.month)
        self.browser['from_b'] = str(today.day)

        self.browser['custom_file_type'] = ['comma_allactivity']
        self.browser['latest_completed_file_type'] = ['']

        self.browser.submit()


class SubmitPage(BasePage):
    """
    Any result of form submission
    """
    def iter_transactions(self, account):
        csv = self.document
        for row in csv.drows:
            # only "real" stuff, no cancelled payments etc.
            if row['Status'] != 'Completed':
                continue
            # we filter accounts by currency
            if account.get_currency(row['Currency']) != account.currency:
                continue
            # does not seem to be a real transaction; duplicates others
            if row['Type'] == u'Authorization':
                continue

            trans = Transaction(row['Transaction ID'])

            # silly American locale
            if re.search(r'\d\.\d\d$', row['Net']):
                date = datetime.datetime.strptime(row['Date'] + ' ' + row['Time'], "%m/%d/%Y %I:%M:%S %p")
            else:
                date = datetime.datetime.strptime(row['Date'] + ' ' + row['Time'], "%d/%m/%Y %H:%M:%S")
            trans.date = date
            trans.rdate = date

            line = row['Name']
            if row['Item Title']:
                line += u' ' + row['Item Title']
            if row['Auction Site']:
                line += u"(" + row['Auction Site'] + u")"
            trans.raw = line
            trans.label = row['Name']

            if row['Type'].endswith(u'Credit Card'):
                trans.type = Transaction.TYPE_CARD
            elif row['Type'].endswith(u'Payment Sent'):
                trans.type = Transaction.TYPE_ORDER
            elif row['Type'] == u'Currency Conversion':
                trans.type = Transaction.TYPE_BANK
            else:
                trans.type = Transaction.TYPE_UNKNOWN

            # Net is what happens after the fee (0 for most users), so what is the most "real"
            trans.amount = clean_amount(row['Net'])
            trans._gross = clean_amount(row['Gross'])
            trans._fees = clean_amount(row['Fee'])

            trans._to = row['To Email Address'] or None
            trans._from = row['From Email Address'] or None

            yield trans


class HistoryParser(CsvParser):
    HEADER = True
    FMTPARAMS = {'skipinitialspace': True}

class UselessPage(BasePage):
    pass

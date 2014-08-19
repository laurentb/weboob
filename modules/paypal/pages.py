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

from decimal import Decimal, InvalidOperation
import re
import datetime

import dateutil.parser

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.parsers.csvparser import CsvParser
from weboob.tools.misc import to_unicode
from weboob.capabilities.bank import Account, Transaction
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['LoginPage', 'AccountPage', 'LastDownloadHistoryPage']

class CSVAlreadyAsked(Exception):
    pass

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
        self.browser['login_email'] = login.encode(self.browser.ENCODING)
        self.browser['login_password'] = password.encode(self.browser.ENCODING)
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
            # XXX it ignores 5+ devises, so it's bad, but it prevents a crash, cf #1216
            try:
                account.balance = clean_amount(balance)
            except InvalidOperation:
                continue
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
    def download(self, start, end):
        tr_last_file_request = self.document.xpath('//table//table//table//tr[2]//td')[1]
        if tr_last_file_request.text is not None:
            last_file_request = tr_last_file_request.text[:-1]
            if dateutil.parser.parse(last_file_request).date() == datetime.date.today():
                raise CSVAlreadyAsked('')
        self.browser.select_form(name='form1')
        self.browser['to_c'] = str(end.year)
        self.browser['to_a'] = str(end.month)
        self.browser['to_b'] = str(end.day)
        self.browser['from_c'] = str(start.year)
        self.browser['from_a'] = str(start.month)
        self.browser['from_b'] = str(start.day)

        self.browser['custom_file_type'] = ['comma_allactivity']
        self.browser['latest_completed_file_type'] = ['']

        self.browser.submit()

class LastDownloadHistoryPage(BasePage):
    def download(self):
        self.browser.select_form(nr=1)
        log_select =  self.document.xpath('//table//form//input[@type="radio"]')[0].attrib['value']
        self.browser['log_select'] = [log_select]
        self.browser.submit()

class SubmitPage(BasePage):
    """
    Any result of form submission
    """
    def iter_transactions(self, account):
        csv = self.document

        if len(csv.header) == 43:
            # Merchant multi-currency account
            DATE = 0
            TIME = 1
            NAME = 3
            TYPE = 4
            CURRENCY = 6
            GROSS = 7
            FEE = 8
            NET = 9
            FROM = 10
            TO = 11
            TRANS_ID = 12
            ITEM = 15
            SITE = 24
        elif len(csv.header) == 11:
            # Regular multi-currency account
            DATE = 0
            TIME = 1
            NAME = 3
            TYPE = 4
            CURRENCY = 6
            GROSS = -1
            FEE = -1
            NET = 7
            FROM = -1
            TO = -1
            TRANS_ID = -1
            ITEM = -1
            SITE = -1
        else:
            raise ValueError('CSV fields count of %i is not supported' % len(csv.header))

        for row in csv.rows:
            # we filter accounts by currency
            if account.get_currency(row[CURRENCY]) != account.currency:
                continue

            # analog to dict.get()
            get = lambda i, v=None: row[i] if 0 <= i < len(row) else v

            trans = Transaction(get(TRANS_ID, u''))

            # silly American locale
            if re.search(r'\d\.\d\d$', row[NET]):
                date = datetime.datetime.strptime(row[DATE] + ' ' + row[TIME], "%m/%d/%Y %H:%M:%S")
            else:
                date = datetime.datetime.strptime(row[DATE] + ' ' + row[TIME], "%d/%m/%Y %H:%M:%S")
            trans.date = date
            trans.rdate = date

            line = row[NAME]
            if get(ITEM):
                line += u' ' + row[ITEM]
            if get(SITE):
                line += u"(" + row[SITE] + u")"
            trans.raw = line
            trans.label = row[NAME]

            if row[TYPE].startswith(u'Update to eCheck') or \
               row[TYPE].startswith(u'Order'):
                continue

            if row[TYPE].endswith(u'Credit Card') or row[TYPE].endswith(u'carte bancaire'):
                trans.type = Transaction.TYPE_CARD
            elif row[TYPE].endswith(u'Payment Sent') or row[TYPE].startswith(u'Paiement'):
                trans.type = Transaction.TYPE_ORDER
            elif row[TYPE] in (u'Currency Conversion', u'Conversion de devise'):
                trans.type = Transaction.TYPE_BANK
            else:
                trans.type = Transaction.TYPE_UNKNOWN

            # Net is what happens after the fee (0 for most users), so what is the most "real"
            trans.amount = clean_amount(row[NET])
            trans._gross = clean_amount(get(GROSS, row[NET]))
            trans._fees = clean_amount(get(FEE, u'0.00'))

            trans._to = get(TO)
            trans._from = get(FROM)

            yield trans


class HistoryParser(CsvParser):
    HEADER = True
    FMTPARAMS = {'skipinitialspace': True}

    def decode_row(self, row, encoding):
        """
        PayPal returns different encodings (latin-1 and utf-8 are know ones)
        """
        return [to_unicode(cell) for cell in row]


class UselessPage(BasePage):
    pass


class HistoryPage(BasePage):
    def guess_format(self):
        rp = re.compile('PAYPAL\.widget\.CalendarLocales\.MDY_([A-Z]+)_POSITION\s*=\s*(\d)')
        rd = re.compile('PAYPAL\.widget\.CalendarLocales\.DATE_DELIMITER\s*=\s*"(.)"')
        rm = re.compile('PAYPAL\.widget\.CalendarLocales\.MONTH_NAMES\s*=\s*\[(.+)\]')
        translate = {'DAY': '%d', 'MONTH': '%m', 'YEAR': '%Y'}
        pos = {}
        delim = '/'
        months = {}
        for script in self.document.xpath('//script'):
            for line in script.text_content().splitlines():
                m = rp.match(line)
                if m and m.groups():
                    pos[int(m.groups()[1])] = translate[m.groups()[0]]
                else:
                    m = rd.match(line)
                    if m:
                        delim = m.groups()[0]
                    else:
                        m = rm.match(line)
                        if m:
                            months = [month.strip("'").strip().lower()[0:3]
                                      for month
                                      in m.groups()[0].split(',')]
        date_format = delim.join((pos[0], pos[1], pos[2]))
        if date_format == "%m/%d/%Y":
            time_format = "%I:%M:%S %p"
        else:
            time_format = "%H:%M:%S"
        return date_format, time_format, months

    def filter(self, start, end):
        date_format = self.guess_format()[0]
        self.browser.select_form(name='history')
        self.browser['dateoption'] = ['dateselect']
        self.browser['from_date'] = start.strftime(date_format)
        self.browser['to_date'] = end.strftime(date_format)
        self.browser.submit(name='show')
        self.browser.select_form(name='history')
        self.browser.submit(name='filter_2')

    def next(self):
        if self.document.xpath('//input[@name="next"]'):
            self.browser.select_form(name='history')
            self.browser.submit(name='next')
            return True

    def parse(self):
        emonths = ['January', 'February', 'March', 'April',
                   'May', 'June', 'July', 'August',
                   'September', 'October', 'November', 'December']
        date_format, time_format, months = self.guess_format()
        for row in self.document.xpath('//table[@id="transactionTable"]/tbody/tr'):
            if len(row.xpath('.//td')) < 5:
                continue

            amount = row.xpath('.//td[@headers="gross"]')[-1].text_content().strip()
            if re.search('\d', amount):
                currency = Account.get_currency(amount)
                amount = clean_amount(amount)
            else:
                continue

            idtext = row.xpath('.//td[@class="detailsNoPrint"]//span[@class="accessAid"]')[0] \
                .text_content().replace(u'\xa0', u' ').strip().rpartition(' ')[-1]
            trans = Transaction(idtext)
            trans.amount = amount
            trans._currency = currency

            datetext = row.xpath('.//td[@class="dateInfo"]')[0].text_content().strip()
            for i in range(0, 12):
                datetext = datetext.replace(months[i], emonths[i])
            date = dateutil.parser.parse(datetext)
            trans.date = date
            trans.rdate = date

            trans.label = to_unicode(row.xpath('.//td[@class="emailInfo"]')[0].text_content().strip())
            info = to_unicode(row.xpath('.//td[@class="paymentTypeInfo"]')[0].text_content().strip())
            trans.raw = info + u' ' + trans.label

            if u'Authorization' in info or u'Autorisation' in info or \
               u'Order' in info:
                continue

            if u'Credit Card' in trans.label or u'Carte bancaire' in trans.label:
                trans.type = Transaction.TYPE_CARD
            elif info.startswith(u'Payment') or info.startswith(u'Paiement'):
                trans.type = Transaction.TYPE_ORDER
            elif u'Currency Conversion' in info or u'Conversion de devise' in info:
                trans.type = Transaction.TYPE_BANK
            else:
                trans.type = Transaction.TYPE_UNKNOWN

            yield trans

    def iter_transactions(self, account):
        for trans in self.parse():
            if trans._currency == account.currency:
                yield trans

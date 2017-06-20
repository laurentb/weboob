# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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


import datetime
import re
from urlparse import urljoin

from weboob.browser.elements import ItemElement, method
from weboob.browser.pages import HTMLPage, LoggedPage, PartialHTMLPage
from weboob.browser.filters.standard import CleanText, CleanDecimal, Currency as CleanCurrency
from weboob.browser.filters.html import Link
from weboob.capabilities.bank import Account
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction
from weboob.tools.date import ChaoticDateGuesser


def parse_decimal(s):
    # we don't know which decimal format this account will use
    comma = s.rfind(',') > s.rfind('.')
    return CleanDecimal(replace_dots=comma).filter(s)


class WrongLoginPage(HTMLPage):
    pass


class AccountSuspendedPage(HTMLPage):
    pass


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='ssoform')
        form['UserID'] = username
        form['USERID'] = username
        form['Password'] = password
        form['PWD'] = password
        form.submit()


class AccountsPage(LoggedPage, PartialHTMLPage):
    def get_account(self):
        for div in self.doc.xpath('.//div[@id="card-details"]'):
            a = Account()
            a.id = CleanText().filter(div.xpath('.//span[@class="acc-num"]'))
            a.label = CleanText().filter(div.xpath('.//span[@class="card-desc"]'))
            if "carte" in a.label.lower():
                a.type = Account.TYPE_CARD
            balance = CleanText().filter(div.xpath('.//span[@class="balance-data"]'))
            if balance in (u'Indisponible', u'Indisponible Facturation en cours', ''):
                a.balance = NotAvailable
            else:
                a.currency = a.get_currency(balance)
                a.balance = - abs(parse_decimal(balance))

            # Cancel card don't have a link to watch history
            link = self.doc.xpath('.//div[@class="wide-bar"]/h3/a')
            if len(link) == 1:
                a.url = urljoin(self.url, link[0].attrib['href'])
            else:
                a.url = None

            return a

    def get_idx_list(self):
        fetched = False
        for div in self.doc.xpath('//div[@id="card-list"]//div[has-class("card-details")]'):
            _id = div.attrib['id']
            idx = re.match(r'card-(\d+)-detail', _id).group(1)

            message = CleanText('.//div[has-class("messages")]')(div).lower()
            cancelled = ('annul' in message or 'cancel' in message)

            yield idx, cancelled
            fetched = True

        if fetched:
            return

        for div in self.doc.xpath('//div[@id="card-detail"]'):
            idx = div.xpath('//span[@id="cardSortedIndex"]/@data')[0]
            message = CleanText('.//div[has-class("messages")]')(div).lower()
            cancelled = ('annul' in message or 'cancel' in message)

            yield idx, cancelled
            return

    def get_session(self):
        return self.doc.xpath('//form[@id="j-session-form"]//input[@name="Hidden"]/@value')


class AccountsPage2(LoggedPage, PartialHTMLPage):
    @method
    class get_account(ItemElement):
        klass = Account

        def parse(self, el):
            assert len(el.xpath('//td[@class="cardArtColWidth"]/div[@class="summaryTitles"]')) == 1, 'fix parsing for multiple accounts'

        obj_id = CleanText('//td[@class="cardArtColWidth"]/div[@class="summaryTitles"]')
        obj_label = CleanText('//span[@class="cardTitle"]')
        obj_type = Account.TYPE_CARD

        obj_currency = CleanCurrency('//td[@id="colOSBalance"]/div[@class="summaryValues makeBold"]')

        def obj_balance(self):
            return -abs(parse_decimal(CleanText('//td[@id="colOSBalance"]/div[@class="summaryValues makeBold"]')(self)))

        def obj_url(self):
            return urljoin(self.page.url, Link('//a[span[text()="Online Statement"]]')(self))


class TransactionsPage(LoggedPage, HTMLPage):
    def is_last(self):
        current = False
        for option in self.doc.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                current = True
            elif current:
                return False

        return True

    def get_end_debit_date(self):
        for option in self.doc.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                m = re.search('(\d+) ([\w\.]+) (\d{4})$', option.text.strip(), re.UNICODE)
                if m:
                    return datetime.date(int(m.group(3)),
                                         self.parse_month(m.group(2)),
                                         int(m.group(1)))

    def get_beginning_debit_date(self):
        for option in self.doc.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                m = re.search('^(\d+) ([\w\.]+) (\d{4})', option.text.strip(), re.UNICODE)
                if m:
                    return datetime.date(int(m.group(3)),
                                         self.parse_month(m.group(2)),
                                         int(m.group(1)))
        return datetime.date.today()

    COL_DATE = 0
    COL_TEXT = 1
    COL_CREDIT = -2
    COL_DEBIT = -1

    FR_MONTHS = ['janv', u'févr', u'mars', u'avr', u'mai', u'juin', u'juil', u'août', u'sept', u'oct', u'nov', u'déc']
    US_MONTHS = ['Jan', u'Feb', u'Mar', u'Apr', u'May', u'Jun', u'Jul', u'Aug', u'Sep', u'Oct', u'Nov', u'Dec']

    @classmethod
    def parse_month(cls, s):
        # there can be fr or us labels even if currency is EUR
        s = s.rstrip('.')
        try:
            return cls.FR_MONTHS.index(s) + 1
        except ValueError:
            return cls.US_MONTHS.index(s) + 1

    def get_history(self, currency):
        # checking if the card is still valid
        if self.doc.xpath('//div[@id="errorbox"]'):
            return

        # adding a time delta because amex have hard time to put the date in a good interval
        beginning_date = self.get_beginning_debit_date() - datetime.timedelta(days=360)
        end_date = self.get_end_debit_date()

        guesser = ChaoticDateGuesser(beginning_date, end_date)

        # Since the site doesn't provide the debit_date,
        # we just use the date of beginning of the previous period.
        # If this date + 1 month is greater than today's date,
        # then the transaction is coming
        previous_text_debit_date = CleanText().filter(self.doc.xpath('//td[@id="colStatementBalance"]/div[3]'))
        if previous_text_debit_date != u'':
            day, month, year = previous_text_debit_date.split()[1:4]
            day = int(day)
            month = self.parse_month(month) + 1
            year = int(year)
            end_of_period = datetime.date(day=day, month=month, year=year)
        else:
            end_of_period = None

        for tr in reversed(self.doc.xpath('//div[@id="txnsSection"]//tbody/tr[@class="tableStandardText"]')):
            cols = tr.findall('td')

            t = Transaction()

            day, month = CleanText().filter(cols[self.COL_DATE]).split(' ', 1)
            day = int(day)
            month = self.parse_month(month)
            date = guesser.guess_date(day, month)

            vdate = None
            try:
                detail = cols[self.COL_TEXT].xpath('./div[has-class("hiddenROC")]')[0]
            except IndexError:
                pass
            else:
                m = re.search(r' (\d{2} \D{3,4})', (' '.join([txt.strip() for txt in detail.itertext()])).strip())
                if m:
                    vday, vmonth = m.group(1).strip().split(' ')
                    vday = int(vday)
                    vmonth = self.parse_month(vmonth)
                    vdate = guesser.guess_date(vday, vmonth)
                detail.drop_tree()

            raw = (' '.join([txt.strip() for txt in cols[self.COL_TEXT].itertext()])).strip()
            credit = CleanText().filter(cols[self.COL_CREDIT])
            debit = CleanText().filter(cols[self.COL_DEBIT])
            if end_of_period is not None and datetime.date.today() < end_of_period:
                t._is_coming = True
            else:
                t._is_coming = False

            t.date = t.rdate = date
            t.vdate = vdate
            t.raw = re.sub(r'[ ]+', ' ', raw)
            t.label = re.sub('(.*?)( \d+)?  .*', r'\1', raw).strip()
            t.amount = parse_decimal(credit or debit) * (1 if credit else -1)
            if t.amount > 0:
                t.type = t.TYPE_ORDER
            else:
                t.type = t.TYPE_DEFERRED_CARD

            yield t

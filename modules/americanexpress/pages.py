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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanText, CleanDecimal
from weboob.capabilities.bank import Account
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction
from weboob.tools.date import ChaoticDateGuesser


class WrongLoginPage(HTMLPage):
    pass


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='ssoform')
        form['UserID'] = username
        form['USERID'] = username
        form['Password'] = password
        form['PWD'] = password
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    def get_list(self):
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
                a.balance = - abs(CleanDecimal(replace_dots=a.currency == 'EUR').filter(balance))

            # Cancel card don't have a link to watch history
            link = self.doc.xpath('.//div[@class="wide-bar"]/h3/a')
            if len(link) == 1:
                a._link = link[0].attrib['href']
            else:
                a._link = None

            yield a


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
                                         self.MONTHS.index(m.group(2).rstrip('.')) + 1,
                                         int(m.group(1)))

    def get_beginning_debit_date(self):
        for option in self.doc.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                m = re.search('^(\d+) ([\w\.]+) (\d{4})', option.text.strip(), re.UNICODE)
                if m:
                    return datetime.date(int(m.group(3)),
                                         self.MONTHS.index(m.group(2).rstrip('.')) + 1,
                                         int(m.group(1)))
        return datetime.date.today()

    COL_DATE = 0
    COL_TEXT = 1
    COL_CREDIT = -2
    COL_DEBIT = -1

    FR_MONTHS = ['janv', u'févr', u'mars', u'avr', u'mai', u'juin', u'juil', u'août', u'sept', u'oct', u'nov', u'déc']
    US_MONTHS = ['Jan', u'Feb', u'Mar', u'Apr', u'May', u'Jun', u'Jul', u'Aug', u'Sep', u'Oct', u'Nov', u'Dec']

    def get_history(self, currency):
        self.MONTHS = self.FR_MONTHS if currency == 'EUR' else self.US_MONTHS
        #checking if the card is still valid
        if self.doc.xpath('//div[@id="errorbox"]'):
            return

        #adding a time delta because amex have hard time to put the date in a good interval
        beginning_date = self.get_beginning_debit_date() - datetime.timedelta(days=300)
        end_date = self.get_end_debit_date()

        guesser = ChaoticDateGuesser(beginning_date, end_date)

        for tr in reversed(self.doc.xpath('//div[@id="txnsSection"]//tr[@class="tableStandardText"]')):
            cols = tr.findall('td')

            t = Transaction()

            day, month = CleanText().filter(cols[self.COL_DATE]).split(' ', 1)
            day = int(day)
            month = self.MONTHS.index(month.rstrip('.')) + 1
            date = guesser.guess_date(day, month)

            rdate = None
            try:
                detail = cols[self.COL_TEXT].xpath('./div[has-class("hiddenROC")]')[0]
            except IndexError:
                pass
            else:
                m = re.search(r' (\d{2} \D{3,4})', (' '.join([txt.strip() for txt in detail.itertext()])).strip())
                if m:
                    rday, rmonth = m.group(1).split(' ')
                    rday = int(rday)
                    rmonth = self.MONTHS.index(rmonth.rstrip('.')) + 1
                    rdate = guesser.guess_date(rday, rmonth)
                detail.drop_tree()

            raw = (' '.join([txt.strip() for txt in cols[self.COL_TEXT].itertext()])).strip()
            credit = CleanText().filter(cols[self.COL_CREDIT])
            debit = CleanText().filter(cols[self.COL_DEBIT])

            t.date = date
            t.rdate = rdate or date
            t.raw = re.sub(r'[ ]+', ' ', raw)
            t.label = re.sub('(.*?)( \d+)?  .*', r'\1', raw).strip()
            t.amount = CleanDecimal(replace_dots=currency == 'EUR').filter(credit or debit) * (1 if credit else -1)
            if t.amount > 0:
                t.type = t.TYPE_ORDER
            else:
                t.type = t.TYPE_CARD

            yield t

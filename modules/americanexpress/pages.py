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
from decimal import Decimal
import re

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.capabilities.bank import Account
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction
from weboob.tools.date import ChaoticDateGuesser


__all__ = ['LoginPage', 'AccountsPage', 'TransactionsPage']


class LoginPage(BasePage):
    def login(self, username, password):
        self.browser.select_form(name='ssoform')
        self.browser.set_all_readonly(False)
        self.browser['UserID'] = username.encode(self.browser.ENCODING)
        self.browser['USERID'] = username.encode(self.browser.ENCODING)
        self.browser['Password'] = password.encode(self.browser.ENCODING)
        self.browser['PWD'] = password.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)



class AccountsPage(BasePage):
    def get_list(self):
        for box in self.document.getroot().cssselect('div.roundedBox div.contentBox'):
            a = Account()
            a.id = self.parser.tocleanstring(box.xpath('.//tr[@id="summaryImageHeaderRow"]//div[@class="summaryTitles"]')[0])
            a.label = self.parser.tocleanstring(box.xpath('.//span[@class="cardTitle"]')[0])
            a.balance = Decimal('0.0')
            coming = self.parser.tocleanstring(self.parser.select(box, 'td#colOSBalance div.summaryValues', 1))
            if coming in (u'Indisponible', ''):
                a.coming = NotAvailable
            else:
                a.coming = - abs(Decimal(Transaction.clean_amount(coming)))
                a.currency = a.get_currency(coming)
            a._link = self.parser.select(box, 'div.summaryTitles a.summaryLink', 1).attrib['href']

            yield a

class TransactionsPage(BasePage):
    COL_ID = 0
    COL_DATE = 1
    COL_DEBIT_DATE = 2
    COL_LABEL = 3
    COL_VALUE = -1


    def is_last(self):
        current = False
        for option in self.document.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                current = True
            elif current:
                return False

        return True

    def get_end_debit_date(self):
        for option in self.document.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                m = re.search('(\d+) ([\w\.]+) (\d{4})$', option.text.strip(), re.UNICODE)
                if m:
                    return datetime.date(int(m.group(3)),
                                         self.MONTHS.index(m.group(2).rstrip('.')) + 1,
                                         int(m.group(1)))
    def get_beginning_debit_date(self):
        for option in self.document.xpath('//select[@id="viewPeriod"]/option'):
            if 'selected' in option.attrib:
                m = re.search('^(\d+) ([\w\.]+) (\d{4})', option.text.strip(), re.UNICODE)
                if m:
                    return datetime.date(int(m.group(3)),
                                         self.MONTHS.index(m.group(2).rstrip('.')) + 1,
                                         int(m.group(1)))

    COL_DATE = 0
    COL_TEXT = 1
    COL_CREDIT = -2
    COL_DEBIT = -1

    MONTHS = ['janv', u'févr', u'mars', u'avr', u'mai', u'juin', u'juil', u'août', u'sept', u'oct', u'nov', u'déc']

    def get_history(self):
        #checking if the card is still valid
        if self.document.xpath('//div[@id="errorbox"]'):
            return

        #adding a time delta because amex have hard time to put the date in a good interval
        beginning_date = self.get_beginning_debit_date() - datetime.timedelta(days=90)
        end_date = self.get_end_debit_date()
        guesser = ChaoticDateGuesser(beginning_date, end_date)

        for tr in reversed(self.document.xpath('//div[@id="txnsSection"]//tr[@class="tableStandardText"]')):
            cols = tr.findall('td')

            t = Transaction(tr.attrib['id'])

            day, month = self.parser.tocleanstring(cols[self.COL_DATE]).split(' ', 1)
            day = int(day)
            month = self.MONTHS.index(month.rstrip('.')) + 1
            date = guesser.guess_date(day, month)

            try:
                detail = self.parser.select(cols[self.COL_TEXT], 'div.hiddenROC', 1)
            except BrokenPageError:
                pass
            else:
                detail.drop_tree()

            raw = (' '.join([txt.strip() for txt in cols[self.COL_TEXT].itertext()])).strip()
            credit = self.parser.tocleanstring(cols[self.COL_CREDIT])
            debit = self.parser.tocleanstring(cols[self.COL_DEBIT])

            t.date = date
            t.rdate = date
            t.raw = re.sub(r'[ ]+', ' ', raw)
            t.label = re.sub('(.*?)( \d+)?  .*', r'\1', raw).strip()
            t.set_amount(credit, debit)
            if t.amount > 0:
                t.type = t.TYPE_ORDER
            else:
                t.type = t.TYPE_CARD

            yield t

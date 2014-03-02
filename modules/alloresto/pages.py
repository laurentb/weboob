# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction


__all__ = ['LoginPage', 'AccountsPage']


class LoginPage(BasePage):
    def login(self, username, password):
        self.browser.select_form(nr=0)
        self.browser['uname'] = username.encode(self.browser.ENCODING)
        self.browser['pass'] = password.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)


class AccountsPage(BasePage):
    def get_list(self):
        a = Account()
        a.id = '0'
        a.label = u'Compte miams'
        a.balance = Decimal(self.parser.tocleanstring(self.document.xpath('//div[@class="compteur"]//strong')[0]))
        a.currency = u'MIAM'
        try:
            a.coming = Decimal(Transaction.clean_amount(self.document.xpath('//table[@id="solde_acquisition_lignes"]//th[@class="col_montant"]')[0].text))
        except BrokenPageError:
            a.coming = Decimal('0')
        yield a

    COL_DATE = 0
    COL_LABEL = 1
    COL_AMOUNT = 2

    MONTHS = ['janv', u'févr', u'mars', u'avr', u'mai', u'juin', u'juil', u'août', u'sept', u'oct', u'nov', u'déc']
    def get_transactions(self, _type='consommable'):
        for tr in self.document.xpath('//table[@id="solde_%s_lignes"]/tbody/tr' % _type):
            cols = tr.findall('td')

            t = Transaction(0)

            day, month, year = self.parser.tocleanstring(cols[self.COL_DATE]).split(' ')
            day = int(day)
            year = int(year)
            month = self.MONTHS.index(month.rstrip('.')) + 1
            date = datetime.date(year, month, day)

            label = self.parser.tocleanstring(cols[self.COL_LABEL])
            t.parse(date, label)
            t.set_amount(self.parser.tocleanstring(cols[self.COL_AMOUNT]))

            yield t

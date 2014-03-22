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

from weboob.tools.browser2.page import HTMLPage, LoggedPage, method, ItemElement
from weboob.tools.browser2.filters import CleanDecimal, CleanText, Filter, TableCell
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction


__all__ = ['LoginPage', 'AccountsPage']


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(nr=1)
        form['uname'] = username
        form['pass'] = password
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ItemElement):
        def __call__(self):
            return self

        klass = Account

        obj_id = '0'
        obj_label = u'Compte miams'
        obj_balance = CleanDecimal('//div[@class="compteur"]//strong')
        obj_currency = u'MIAM'
        obj_coming = CleanDecimal('//table[@id="solde_acquisition_lignes"]//th[@class="col_montant"]', default=Decimal('0'))

    class MyDate(Filter):
        MONTHS = ['janv', u'févr', u'mars', u'avr', u'mai', u'juin', u'juil', u'août', u'sept', u'oct', u'nov', u'déc']
        def filter(self, txt):
            day, month, year = txt.split(' ')
            day = int(day)
            year = int(year)
            month = self.MONTHS.index(month.rstrip('.')) + 1
            return datetime.date(year, month, day)

    def get_transactions(self, type='consommable'):
        class get_history(Transaction.TransactionsElement):
            head_xpath = '//table[@id="solde_%s_lignes"]//thead//tr/th/text()' % type
            item_xpath = '//table[@id="solde_%s_lignes"]//tbody/tr' % type

            col_date = u"Date de valeur"
            col_raw = u"Motif"

            class item(Transaction.TransactionElement):
                obj_amount = Transaction.Amount('./td[last()]')
                obj_date = AccountsPage.MyDate(CleanText(TableCell('date')))

        return get_history(self)()

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


import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import Regexp, CleanText, CleanDecimal, Format
from weboob.browser.filters.html import Link

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(HTMLPage):
    def enter_login(self, username):
        form = self.get_form(nr=1)
        form['name'] = username
        form.submit()

    def enter_password(self, password):
        form = self.get_form(nr=1)
        form['pass'] = password
        form.submit()


class HomePage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '//div[@class="three_contenu_table"]'

        class item(ItemElement):
            klass = Account

            def condition(self):
                return len(self.el.xpath('.//div[@class="catre_col_two"]/h2')) > 0

            obj_id = CleanText('.//div[@class="carte_col_leftcol"]/p') & Regexp(pattern=r'(\d+)')
            obj_label = CleanText('.//div[@class="carte_col_leftcol"]/h2')
            obj_balance = Format('-%s', CleanText('.//div[@class="catre_col_two"]/h2')) & CleanDecimal(replace_dots=True)
            obj_currency = FrenchTransaction.Currency('.//div[@class="catre_col_two"]/h2')
            obj__link = Link('.//a[contains(@href, "solde-dernieres-operations")]')


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>.*?) (?P<dd>\d{2})/(?P<mm>\d{2})$'), FrenchTransaction.TYPE_CARD)]


class TransactionsPage(LoggedPage, HTMLPage):
    @method
    class get_history(Transaction.TransactionsElement):
        head_xpath = '//table[@id="creditHistory"]//thead/tr/th'
        item_xpath = '//table[@id="creditHistory"]/tbody/tr'

        class item(Transaction.TransactionElement):
            obj_id = None
            obj_type = Transaction.TYPE_CARD

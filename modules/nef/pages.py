# -*- coding: utf-8 -*-

# Copyright(C) 2019      Damien Cassou
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

from __future__ import unicode_literals

import re

from weboob.browser.elements import ListElement, DictElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Field, Date
from weboob.browser.pages import HTMLPage, PartialHTMLPage, CsvPage, LoggedPage
from weboob.browser.filters.json import Dict

from weboob.capabilities.bank import Account

from weboob.tools.date import parse_french_date

from .transaction import Transaction

class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='formSignon')
        form['userId'] = username
        form['logonId'] = username
        form['static'] = password
        form.submit()

class HomePage(LoggedPage, HTMLPage):
    pass

class AccountsPage(LoggedPage, PartialHTMLPage):
    ACCOUNT_TYPES = {re.compile('livret'):           Account.TYPE_SAVINGS,
                     re.compile('parts sociales'):   Account.TYPE_SAVINGS,
                    }

    @method
    class get_items(ListElement):
        item_xpath = '//div[@data-type="account"]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('.//div/div/div[(position()=3) and (has-class("pc-content-text"))]/span') & Regexp(pattern=r'(\d+) ')
            obj_label = CleanText('.//div/div/div[(position()=2) and (has-class("pc-content-text-wrap"))]')
            obj_balance = CleanDecimal('./div[position()=3]/span', replace_dots=True)
            obj_currency = u'EUR'

            def obj_type(self):
                label = Field('label')(self).lower()

                for regex, account_type in self.page.ACCOUNT_TYPES.items():
                    if (regex.match(label)):
                        return account_type

                return Account.TYPE_UNKNOWN

class TransactionsPage(LoggedPage, CsvPage):
    ENCODING = 'latin-1'
    DIALECT = 'excel'

    # lines 1 to 5 are meta-data
    # line 6 is empty
    # line 7 describes the columns
    HEADER = 7

    @method
    class iter_history(DictElement):
        class item(ItemElement):
            klass = Transaction

            # The CSV contains these columns:
            #
            # "Date opération","Date Valeur","Référence","Montant","Solde","Libellé"
            obj_raw = Transaction.Raw(Dict(u'Libellé'))
            obj_amount = CleanDecimal(Dict('Montant'), replace_dots=True)
            obj_date = Date(Dict('Date opération'), parse_func=parse_french_date, dayfirst=True)
            obj_vdate = Date(Dict('Date Valeur'), parse_func=parse_french_date, dayfirst=True)

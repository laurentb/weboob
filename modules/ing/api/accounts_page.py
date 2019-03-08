# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Eval,
)
from weboob.capabilities.bank import Account, Transaction


class AccountsPage(LoggedPage, JsonPage):
    @method
    class iter_accounts(DictElement):
        item_xpath = 'accounts'

        class item(ItemElement):
            klass = Account

            obj_id = Dict('uid')
            obj_label = Dict('type/label')
            obj_number = CleanText(Dict('label'), replace=[(' ', '')])

            def obj_balance(self):
                if not Dict('hasPositiveBalance')(self):
                    return -CleanDecimal(Dict('ledgerBalance'))(self)
                return CleanDecimal(Dict('ledgerBalance'))(self)


class HistoryPage(LoggedPage, JsonPage):
    def is_empty_page(self):
        return len(self.doc) == 0

    @method
    class iter_history(DictElement):
        class item(ItemElement):
            klass = Transaction

            obj_id = Eval(str, Dict('id'))
            obj_label = CleanText(Dict('detail'))
            obj_amount = CleanDecimal(Dict('amount'))
            obj_date = Date(Dict('effectiveDate'))


class ComingPage(LoggedPage, JsonPage):
    @method
    class iter_coming(DictElement):
        item_xpath = 'futureOperations'

        class item(ItemElement):
            klass = Transaction

            obj_label = Dict('label')
            obj_amount = CleanDecimal(Dict('amount'))
            obj_date = Date(Dict('effectiveDate'))
            obj_vdate = Date(Dict('operationDate'))

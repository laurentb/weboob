# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import re

from weboob.browser.pages import JsonPage, LoggedPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.standard import CleanText, Date, Regexp, CleanDecimal, Env, Field
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(JsonPage):
    def get_session_id(self):
        return Dict('sessionId')(self.doc)

    def get_information(self, information):
        return Dict(information, default=None)(self.doc)


class AccountsPage(LoggedPage, JsonPage):
    @method
    class get_account(ItemElement):
        klass = Account

        obj_balance = CleanDecimal(Dict('totalPortfolio/value/2/value'))

        def obj_id(self):
            return str(self.page.browser.intAccount)

        def obj_label(self):
            return '%s DEGIRO' % self.page.browser.name.title()

        def obj_type(self):
            return Account.TYPE_MARKET

        def obj_currency(self):
            for currency in Dict('cashFunds/value')(self):
                if Dict('value/2/value' % currency)(currency) != 0:
                    return Dict('value/1/value')(currency)

    @method
    class iter_investment(DictElement):
        item_xpath = 'portfolio/value'

        class item(ItemElement):
            klass = Investment

            obj__product_id = CleanText(Dict('value/0/value'))
            obj_quantity = CleanDecimal(Dict('value/2/value'))
            obj_unitvalue = CleanDecimal(Dict('value/3/value'))
            obj_valuation = CleanDecimal(Dict('value/6/value'))

            def obj_code(self):
                s = Field('_product_id')(self)
                return self.page.browser.search_product(s)

            def condition(self):
                return Field('quantity')(self) > 0


class InvestmentPage(LoggedPage, JsonPage):
    pass


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^Deposit.*'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(Buy.*|Sell.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class HistoryPage(LoggedPage, JsonPage):
    @method
    class iter_history(DictElement):
        item_xpath = 'data/cashMovements'

        class item(ItemElement):
            klass = Transaction

            obj_raw = Transaction.Raw(CleanText(Dict('description')))
            obj_date = Date(CleanText(Dict('date')), dayfirst=True)
            obj_amount = CleanDecimal(Dict('change'))

            obj__isin = Regexp(Dict('description'), r'\((.*?)\)', default=None)

            obj__datetime = Dict('date')

            def obj_investments(self):
                if Field('_isin')(self):
                    return [inv for inv in Env('transaction_investments')(self).v if inv.code == Field('_isin')(self) and inv._action == Field('raw')(self)[0] and inv._datetime == Field('_datetime')(self)]
                return []

    @method
    class iter_transaction_investments(DictElement):
        item_xpath = 'data'

        class item(ItemElement):
            klass = Investment

            obj__product_id = CleanDecimal(Dict('productId'))
            obj_quantity = CleanDecimal(Dict('quantity'))
            obj_unitvalue = CleanDecimal(Dict('price'))
            obj_vdate = Date(CleanText(Dict('date')), dayfirst=True)
            obj__action = Dict('buysell')

            obj__datetime = Dict('date')

            def obj_code(self):
                s = str(Field('_product_id')(self))
                return self.page.browser.search_product(s)

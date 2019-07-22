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

from __future__ import unicode_literals

from decimal import Decimal
import re

from weboob.browser.pages import JsonPage, LoggedPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.standard import (
    CleanText, Date, Regexp, CleanDecimal, Env, Field, Currency,
)
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, empty, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.exceptions import AuthMethodNotImplemented
from weboob.tools.capabilities.bank.investments import is_isin_valid


def float_to_decimal(f):
    return Decimal(str(f))


class LoginPage(JsonPage):
    def on_load(self):
        if Dict('statusText', default="")(self.doc) == "totpNeeded":
            raise AuthMethodNotImplemented("Time-based One-time Password is not supported")

    def get_session_id(self):
        return Dict('sessionId')(self.doc)

    def get_information(self, information):
        key = 'data/' + information
        return Dict(key, default=None)(self.doc)


def list_to_dict(l):
    return {d['name']: d.get('value') for d in l}


# Specific currencies are displayed with a factor
# in the API so we must divide the invest valuations
SPECIFIC_CURRENCIES = {
    'JPY': 100,
}

class AccountsPage(LoggedPage, JsonPage):
    @method
    class get_account(ItemElement):
        klass = Account

        # account balance will be filled with the
        # sum of its investments in browser.py

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

            def condition(self):
                return float_to_decimal(list_to_dict(self.el['value'])['size'])

            obj_unitvalue = Env('unitvalue', default=NotAvailable)
            obj_original_currency = Env('original_currency', default=NotAvailable)
            obj_original_unitvalue = Env('original_unitvalue', default=NotAvailable)
            obj_valuation = Env('valuation')

            def obj__product_id(self):
                return str(list_to_dict(self.el['value'])['id'])

            def obj_quantity(self):
                return float_to_decimal(list_to_dict(self.el['value'])['size'])

            def obj_unitprice(self):
                return float_to_decimal(list_to_dict(self.el['value'])['breakEvenPrice'])

            def obj_label(self):
                return self._product()['name']

            def obj_vdate(self):
                vdate = self._product().get('closePriceDate')  # .get() because certain invest don't have that key in the json
                if vdate:
                    return Date().filter(vdate)
                return NotAvailable

            def obj_code(self):
                code = self._product()['isin']
                if is_isin_valid(code):
                    # Prefix CFD (Contrats for difference) ISIN codes with "XX-"
                    # to avoid id_security duplicates in the database
                    if "- CFD" in Field('label')(self):
                        return "XX-" + code
                    return code
                return NotAvailable

            def obj_code_type(self):
                if empty(Field('code')(self)):
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN

            def _product(self):
                return self.page.browser.get_product(str(Field('_product_id')(self)))

            def parse(self, el):
                currency = self._product()['currency']
                unitvalue = float_to_decimal(list_to_dict(self.el['value'])['price'])
                valuation = float_to_decimal(list_to_dict(self.el['value'])['value'])
                self.env['valuation'] = valuation / SPECIFIC_CURRENCIES.get(currency, 1)

                if currency == self.env['currency']:
                    self.env['unitvalue'] = unitvalue
                else:
                    self.env['original_unitvalue'] = unitvalue

                self.env['original_currency'] = currency


class InvestmentPage(LoggedPage, JsonPage):
    def get_products(self):
        return self.doc.get('data', [])


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(Deposit|Versement)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(Buy|Sell|Achat|Vente)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class HistoryPage(LoggedPage, JsonPage):
    @method
    class iter_history(DictElement):
        item_xpath = 'data/cashMovements'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                # Transactions without amount are ignored even on the website
                return Dict('change', default=None)(self)

            obj_raw = Transaction.Raw(CleanText(Dict('description')))
            obj_date = Date(CleanText(Dict('date')))
            obj__isin = Regexp(Dict('description'), r'\((.{12}?)\)', nth=-1, default=None)
            obj__number = Regexp(Dict('description'), r'^([Aa]chat|[Vv]ente|[Bb]uy|[Ss]ell) (\d+[,.]?\d*)', template='\\2', default=None)
            obj__datetime = Dict('date')

            def obj__action(self):
                if not Field('_isin')(self):
                    return

                label = Field('raw')(self).split()[0]
                return {
                    'Buy': 'B',
                    'Achat': 'B',
                    'Compra': 'B',
                    'Sell': 'S',
                    'Vente': 'S',
                    'Venta': 'S',
                    'Venda': 'S',
                    'Taxe': None,
                    'Frais': None,
                    'Intérêts': None,
                    'Comisión': None,
                    'Custo': None,
                    'DEGIRO': None,
                    # make sure we don't miss transactions labels specifying an ISIN
                }[label]

            def obj_amount(self):
                if Env('account_currency')(self) == Dict('currency')(self):
                    return float_to_decimal(Dict('change')(self))
                # The amount is not displayed so we only retrieve the original_amount
                return NotAvailable

            def obj_original_amount(self):
                if Env('account_currency')(self) == Dict('currency')(self):
                    return NotAvailable
                return float_to_decimal(Dict('change')(self))

            def obj_original_currency(self):
                if Env('account_currency')(self) == Dict('currency')(self):
                    return NotAvailable
                return Currency(Dict('currency'))(self)

            def obj_investments(self):
                tr_investment_list = Env('transaction_investments')(self).v
                isin = Field('_isin')(self)
                action = Field('_action')(self)
                if isin and action:
                    tr_inv_key = (isin, action, Field('_datetime')(self))
                    try:
                        return [tr_investment_list[tr_inv_key]]
                    except KeyError:
                        pass
                return []

            def validate(self, obj):
                assert not empty(obj.amount) or not empty(obj.original_amount), 'This transaction has no amount and no original_amount!'
                return True


    @method
    class iter_transaction_investments(DictElement):
        item_xpath = 'data'

        class item(ItemElement):
            klass = Investment

            obj__product_id = Dict('productId')
            obj_quantity = CleanDecimal(Dict('quantity'))
            obj_unitvalue = CleanDecimal(Dict('price'))
            obj_vdate = Date(CleanText(Dict('date')))
            obj__action = Dict('buysell')
            obj__datetime = Dict('date')

            def _product(self):
                return self.page.browser.get_product(str(Field('_product_id')(self)))

            def obj_label(self):
                return self._product()['name']

            def obj_code(self):
                code = self._product()['isin']
                if is_isin_valid(code):
                    # Prefix CFD (Contrats for difference) ISIN codes with "XX-"
                    # to avoid id_security duplicates in the database
                    if "- CFD" in Field('label')(self):
                        return "XX-" + code
                    return code
                return NotAvailable

            def obj_code_type(self):
                if empty(Field('code')(self)):
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN

    def get_products(self):
        return set(d['productId'] for d in self.doc['data'])

# -*- coding: utf-8 -*-

# Copyright(C) 2018      Fong Ngo
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

from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    Date, CleanDecimal, Eval, Field, Env, Regexp, Format,
)
from weboob.browser.pages import JsonPage, HTMLPage, LoggedPage
from weboob.capabilities.bank import Investment, Transaction
from weboob.capabilities.base import NotAvailable, empty
from weboob.tools.capabilities.bank.investments import is_isin_valid


class AccountPage(LoggedPage, JsonPage):
    def get_ncontrat(self):
        return self.doc['identifiantContratCrypte']


class PortfolioPage(LoggedPage, JsonPage):
    def get_valuation_diff(self):
        return CleanDecimal(Dict('totalPlv'))(self.doc)  # Plv = plus-value

    def get_date(self):
        return Date(Regexp(Dict('dateValo'), r'(\d{2})(\d{2})(\d{2})', '\\3\\2\\1'), dayfirst=True)(self.doc)

    @method
    class iter_investments(DictElement):
        item_xpath = 'listeSegmentation/*'  # all categories are fetched: obligations, actions, OPC

        class item(ItemElement):
            klass = Investment

            def condition(self):
                # Some rows do not contain an expected item format,
                # There is no valuation (mnt) because some buy/sell orders are not yet finished.
                # We want invalid values to fail in the CleanDecimal filter so we catch only when mnt is missing
                return Dict('mnt', default=NotAvailable)(self) is not NotAvailable

            obj_label = Dict('libval')
            obj_code = Dict('codval')
            obj_code_type = Eval(
                lambda x: Investment.CODE_TYPE_ISIN if is_isin_valid(x) else NotAvailable,
                Field('code')
            )
            obj_quantity = CleanDecimal(Dict('qttit'))
            obj_unitvalue = CleanDecimal(Dict('crs'))
            obj_valuation = CleanDecimal(Dict('mnt'))
            obj_vdate = Env('date')

            def parse(self, el):
                symbols = {
                    '+': 1,
                    '-': -1,
                    '\u0000': None,  # "NULL" character
                }
                self.env['sign'] = symbols.get(Dict('signePlv')(self), None)

            def obj_diff(self):
                if Dict('plv', default=None)(self) and Env('sign')(self):
                    return CleanDecimal(Dict('plv'), sign=lambda x: Env('sign')(self))(self)
                return NotAvailable

            def obj_unitprice(self):
                if Dict('pam', default=None)(self):
                    return CleanDecimal(Dict('pam'))(self)
                return NotAvailable

            def obj_diff_ratio(self):
                if not Env('sign')(self):
                    return NotAvailable
                # obj_diff_ratio key can have several names:
                if Dict('plvPourcentage', default=None)(self):
                    return CleanDecimal(Dict('plvPourcentage'), sign=lambda x: Env('sign')(self))(self)
                elif Dict('pourcentagePlv', default=None)(self):
                    return CleanDecimal(Dict('pourcentagePlv'), sign=lambda x: Env('sign')(self))(self)

            def obj_portfolio_share(self):
                active_percent = Dict('pourcentageActif', default=NotAvailable)(self)
                if empty(active_percent):
                    return NotAvailable
                return Eval(lambda x: x / 100, CleanDecimal(active_percent))(self)


class AccountCodesPage(LoggedPage, JsonPage):
    def get_contract_number(self, account_id):
        for acc in self.doc['data']:
            if account_id in acc['affichage']:
                return acc['identifiantContratCrypte']
        assert False, 'the account code was not found in the linebourse API'


class NewWebsiteFirstConnectionPage(LoggedPage, JsonPage):
    def build_doc(self, content):
        content = JsonPage.build_doc(self, content)
        if 'data' in content:
            # The value contains HTML
            # Must be encoded into str because HTMLPage.build_doc() uses BytesIO
            # which expects bytes
            html_page = HTMLPage(self.browser, self.response)
            return html_page.build_doc(content['data'].encode(self.encoding))
        return content


class HistoryAPIPage(LoggedPage, JsonPage):
    @method
    class iter_history(DictElement):
        item_xpath = 'data/lstOperations'

        class item(ItemElement):
            klass = Transaction

            obj_label = Format('%s %s (%s)', Dict('libNatureOperation'), Dict('libValeur'), Dict('codeValeur'))
            obj_amount = CleanDecimal(Dict('mntNet'))
            obj_date = Date(Dict('dtOperation'))
            obj_rdate = Date(Dict('dtOperation'))
            obj_type = Transaction.TYPE_BANK

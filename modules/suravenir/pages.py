# -*- coding: utf-8 -*-
# Copyright(C) 2018 Arthur Huillet
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

from weboob.browser.elements import ListElement, TableElement, ItemElement, method
from weboob.browser.filters.html import AbsoluteLink, TableCell, Link
from weboob.browser.filters.standard import CleanText, CleanDecimal, Date
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.browser.pages import HTMLPage, LoggedPage, pagination


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form(id='_58_fm')
        form['_58_login'] = login
        form['_58_password'] = passwd
        form.submit()


class AccountsList(LoggedPage, HTMLPage):
    @method
    class get_contracts(ListElement):
        item_xpath = '//tr[contains(@class, "results-row")]'

        class item(ItemElement):
            klass = Account

            obj_label = CleanText('./td[contains(@class, "col-1")]/a')
            obj_id = CleanText('./td[contains(@class, "col-2")]/a', replace=[(' ', '')])
            obj_balance = CleanDecimal('./td[contains(@class, "col-3")]', replace_dots=True)
            obj__detail_link = AbsoluteLink('./td[contains(@class, "col-2")]/a')
            obj_type = Account.TYPE_LIFE_INSURANCE


class InvestmentList(LoggedPage, HTMLPage):
    @method
    class iter_investments(TableElement):
        head_xpath = '//thead[@class="table-columns"]/tr/th/text()'
        item_xpath = '//tbody[@class="table-data"]/tr[contains(@class, "results-row")]'

        col_ISIN = u"Code ISIN"
        col_fund = u"Libellé support"
        col_qty =  u"Nb parts"
        col_date = u"Date VL*"
        col_unitvalue =  u"VL*"
        col_unitprice =  u"Prix de revient"
        col_perf = u"Perf."
        col_valuation = u"Solde"

        class item(ItemElement):
            klass = Investment
            obj_label = CleanText(TableCell("fund"))
            obj_description = obj_label
            obj_code = CleanText(TableCell("ISIN"), default=NotAvailable)
            obj_code_type = Investment.CODE_TYPE_ISIN
            obj_quantity = CleanDecimal(TableCell("qty"), replace_dots=True, default=NotAvailable)
            obj_unitprice = CleanDecimal(TableCell("unitprice"), replace_dots=True, default=NotAvailable)
            obj_unitvalue = CleanDecimal(TableCell("unitvalue"), replace_dots=True, default=NotAvailable)
            obj_valuation = CleanDecimal(TableCell("valuation"), replace_dots=True, default=NotAvailable)
            obj_vdate = Date(CleanText(TableCell("date")), dayfirst=True, default=NotAvailable)
            obj_diff_percent = CleanDecimal(TableCell("perf"), replace_dots=True, default=NotAvailable)


class AccountHistory(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_history(TableElement):
        next_page = Link('(//ul[contains(@class, "lfr-pagination-buttons")])[2]/li[@class=" next"]/a[contains(text(), "Suivant")]')
        head_xpath = '//thead[@class="table-columns"]/tr/th/div/a/text()[1]'
        item_xpath = '//tbody[@class="table-data"]/tr[contains(@class, "results-row")]'

        col_date   = u"Date de l'opération"
        col_label  = u"Libellé de l'opération"
        col_amount = u"Montant"

        class item(ItemElement):
            klass = Transaction
            obj_date = Date(CleanText(TableCell("date")), dayfirst=True, default=NotAvailable)
            obj_raw = CleanText(TableCell("label"))
            obj_label = CleanText(TableCell("label"))
            obj_amount = CleanDecimal(TableCell("amount"), replace_dots=True, default=NotAvailable)

            def obj__transaction_detail(self):
                return AbsoluteLink((TableCell("label")(self)[0]).xpath('.//a'))

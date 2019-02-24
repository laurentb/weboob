# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget-Insight
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

import re
from decimal import Decimal
import datetime

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import method, ItemElement, TableElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, Currency
from weboob.browser.filters.html import TableCell, Attr
from weboob.capabilities.bank import Investment, Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.investments import is_isin_valid, create_french_liquidity


class AccountsPage(LoggedPage, HTMLPage):

    # UTF8 tag in the meta div, but that's wrong
    ENCODING = 'iso-8859-1'

    @method
    class get_accounts(TableElement):

        head_xpath = '//table[contains(@class,"tableau_comptes_details")]//th'

        # There is not 'tbody' balise in the table, we have to get all tr and get out thead and tfoot ones
        item_xpath = '//table[contains(@class,"tableau_comptes_details")]//tr[not(ancestor::thead) and not(ancestor::tfoot)]'

        col_id = col_label = 'Comptes'
        col_owner = 'Titulaire du compte'
        col_balance = re.compile(r'.*Valorisation totale.*')

        class item(ItemElement):
            klass = Account

            obj_owner = CleanText(TableCell('owner'))
            obj_type = Account.TYPE_MARKET

            def obj_id(self):
                tablecell = TableCell('id')(self)[0]
                id = tablecell.xpath('./div[position()=2]')
                return CleanText().filter(id)

            def obj_label(self):
                tablecell = TableCell('label')(self)[0]
                label = tablecell.xpath('./div[position()=1]')
                return CleanText(label)(self)

            def obj_balance(self):
                tablecell = TableCell('balance')(self)[0]
                b = tablecell.xpath('./span[@class="intraday"]')
                balance = CleanDecimal(replace_dots=True).filter(b)
                return Decimal(balance)

            def obj_currency(self):
                tablecell = TableCell('balance')(self)[0]
                text = tablecell.xpath('./span/text()')[0]
                regex = '[0-9,.]* (.*)'
                currency = Currency().filter(re.search(regex, text).group(1))

                return currency

    def get_nump_id(self, account):
        # Return an element needed in the request in order to access investments details
        attr = Attr('//td[contains(@id, "wallet-%s")]' % account.id, 'onclick')(self.doc)
        return re.search('([0-9]+:[0-9]+)', attr).group(1)


class InvestmentsPage(LoggedPage, HTMLPage):

    # UTF8 tag in the meta div, but that's wrong
    ENCODING = 'iso-8859-1'

    @method
    class get_investments(TableElement):

        item_xpath = '//table[@id="tableValeurs"]/tbody/tr[starts-with(@id, "ContentDetPosInLine")]'
        head_xpath = '//table[@id="tableValeurs"]/thead//th'

        col_label = col_code = 'Valeur / Isin'
        col_quantity = ['Quantité', 'Qté']
        col_unitvalue = col_vdate = 'Cours'
        col_valuation = ['Valorisation totale', 'Val. totale']
        col_unitprice = 'Prix de revient'
        col_diff = '+/- Value latente'

        # Due to a bug in TableCell, column's number match with tdcell-1
        # Had to use <following-sibling::td[position()=1]> each time in xpath to get the right cell
        # @todo : Correct the TableCell class and this module

        class item(ItemElement):
            klass = Investment

            obj_diff = CleanDecimal(TableCell('diff', colspan=True), replace_dots=True)
            obj_unitprice = CleanDecimal(TableCell('unitprice', colspan=True), replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation', colspan=True), replace_dots=True)

            def obj_quantity(self):
                tablecell = TableCell('quantity', colspan=True)(self)[0]
                return CleanDecimal(tablecell.xpath('./span'), replace_dots=True)(self)

            def obj_label(self):
                tablecell = TableCell('label', colspan=True)(self)[0]
                label = CleanText(tablecell.xpath('./following-sibling::td[@class=""]/div/a')[0])(self)
                return label

            def obj_code(self):
                # We try to get the code from <a> div. If we didn't find code in url,
                # we try to find it in the cell text

                tablecell = TableCell('label', colspan=True)(self)[0]
                # url find try
                url = tablecell.xpath('./following-sibling::td[position()=1]/div/a')[0].attrib['href']
                code_match = re.search(r'sico=([A-Z0-9]*)', url)

                if code_match:
                    if is_isin_valid(code_match.group(1)):
                        return code_match.group(1)

                # cell text find try
                text = CleanText(tablecell.xpath('./following-sibling::td[position()=1]/div')[0])(self)

                for code in text.split(' '):
                    if is_isin_valid(code):
                        return code
                return NotAvailable

            def obj_code_type(self):
                if is_isin_valid(self.obj_code()):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable


            def obj_unitvalue(self):
                currency, unitvalue = self.original_unitvalue()

                if currency == self.env['account_currency']:
                    return unitvalue
                return NotAvailable

            def obj_original_currency(self):
                currency, unitvalue = self.original_unitvalue()

                if currency != self.env['account_currency']:
                    return currency

            def obj_original_unitvalue(self):
                currency, unitvalue = self.original_unitvalue()

                if currency != self.env['account_currency']:
                    return unitvalue

            def obj_vdate(self):
                tablecell = TableCell('vdate', colspan=True)(self)[0]
                vdate_scrapped = tablecell.xpath('./preceding-sibling::td[position()=1]//span/text()')[0]

                # Scrapped date could be a schedule time (00:00) or a date (01/01/1970)
                vdate = NotAvailable

                if ':' in vdate_scrapped:
                    today = datetime.date.today()
                    h, m = [int(x) for x in vdate_scrapped.split(':')]
                    hour = datetime.time(hour=h, minute=m)
                    vdate = datetime.datetime.combine(today, hour)

                elif '/' in vdate_scrapped:
                    vdate = datetime.datetime.strptime(vdate_scrapped, '%d/%m/%y')

                return vdate

            # extract unitvalue and currency
            def original_unitvalue(self):
                tablecell = TableCell('unitvalue', colspan=True)(self)[0]
                text = tablecell.xpath('./text()')[0]

                regex = '[0-9,]* (.*)'
                currency = Currency().filter(re.search(regex, text).group(1))

                return currency, CleanDecimal(replace_dots=True).filter(text)

    def get_liquidity(self):
        liquidity_element = self.doc.xpath('//td[contains(text(), "Solde espèces en euros")]//following-sibling::td[position()=1]')
        assert len(liquidity_element) <= 1
        if liquidity_element:
            valuation = CleanDecimal(replace_dots=True).filter(liquidity_element[0])
            return create_french_liquidity(valuation)

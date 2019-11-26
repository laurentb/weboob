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
import datetime

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import method, ItemElement, TableElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, Currency, Map, Field, Regexp
from weboob.browser.filters.html import TableCell, Attr, Link
from weboob.capabilities.bank import Investment, Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.investments import is_isin_valid, create_french_liquidity, IsinType


ACCOUNT_TYPES = {
    'D.A.T.': Account.TYPE_DEPOSIT,
    'COMPTE PEA': Account.TYPE_PEA,
    'INTEGRAL PEA': Account.TYPE_PEA,
    'COMPTE PEA-PME': Account.TYPE_PEA,
    'INTEGRAL C.T.O.': Account.TYPE_MARKET,
    'COMPTE TITRES': Account.TYPE_MARKET,
    'CTO VENDOME PRIVILEGE': Account.TYPE_MARKET,
    'PARTS SOCIALES': Account.TYPE_MARKET,
    'PEA VENDOME PATRIMOINE': Account.TYPE_PEA,
}

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

            obj_type = Map(Field('label'), ACCOUNT_TYPES, Account.TYPE_UNKNOWN)
            obj__owner = CleanText(TableCell('owner'))

            def obj_id(self):
                tablecell = TableCell('id')(self)[0]
                _id = tablecell.xpath('./div[position()=2]')
                return CleanText(_id)(self)

            obj_number = obj_id

            def obj_label(self):
                tablecell = TableCell('label')(self)[0]
                label = tablecell.xpath('./div[position()=1]')
                return CleanText(label)(self)

            def obj_balance(self):
                tablecell = TableCell('balance')(self)[0]
                balance = tablecell.xpath('./span[@class="intraday"]')
                return CleanDecimal.French(balance)(self)

            def obj_currency(self):
                tablecell = TableCell('balance')(self)[0]
                currency = tablecell.xpath('./span[@class="intraday"]')
                return Currency(currency)(self)


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

            obj_valuation = CleanDecimal.French(TableCell('valuation'))
            obj_diff = CleanDecimal.French(TableCell('diff'))

            # Some invests have a format such as '22,120' but some others have '0,7905 (79,05%)'
            obj_unitprice = CleanDecimal.French(
                Regexp(
                    CleanText(TableCell('unitprice')),
                    r'([0-9]+,[0-9]+)',
                    default=NotAvailable
                ),
                default=NotAvailable
            )

            def obj_quantity(self):
                tablecell = TableCell('quantity')(self)[0]
                return CleanDecimal.French(tablecell.xpath('./span'))(self)

            def obj_label(self):
                tablecell = TableCell('label')(self)[0]
                return CleanText(tablecell.xpath('./following-sibling::td[@class=""]/div/a')[0])(self)

            def obj_code(self):
                # We try to get the code from <a> div. If we didn't find code in url,
                # we try to find it in the cell text
                tablecell = TableCell('label')(self)[0]
                # url find try
                code_match = Regexp(
                    Link(tablecell.xpath('./following-sibling::td[position()=1]/div/a')),
                    r'sico=([A-Z0-9]*)',
                    default=None
                )(self)
                if is_isin_valid(code_match):
                    return code_match

                # cell text find try
                text = CleanText(tablecell.xpath('./following-sibling::td[position()=1]/div')[0])(self)

                for code in text.split(' '):
                    if is_isin_valid(code):
                        return code
                return NotAvailable

            obj_code_type = IsinType(Field('code'))

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
                tablecell = TableCell('vdate')(self)[0]
                vdate_scraped = tablecell.xpath('./preceding-sibling::td[position()=1]//span/text()')[0]

                # Scrapped date could be a schedule time (00:00) or a date (01/01/1970)
                vdate = NotAvailable

                if ':' in vdate_scraped:
                    today = datetime.date.today()
                    h, m = [int(x) for x in vdate_scraped.split(':')]
                    hour = datetime.time(hour=h, minute=m)
                    vdate = datetime.datetime.combine(today, hour)

                elif '/' in vdate_scraped:
                    vdate = datetime.datetime.strptime(vdate_scraped, '%d/%m/%y')

                return vdate

            # extract unitvalue and currency
            def original_unitvalue(self):
                tablecell = TableCell('unitvalue')(self)[0]
                text = tablecell.xpath('./text()')
                return Currency(text, default=NotAvailable)(self), CleanDecimal.French(text, default=NotAvailable)(self)

    def get_liquidity(self):
        # Not all accounts have a Liquidity element
        liquidity_element = CleanDecimal.French('//td[contains(text(), "Solde espèces en euros")]//following-sibling::td[position()=1]', default=None)(self.doc)
        if liquidity_element:
            return create_french_liquidity(liquidity_element)

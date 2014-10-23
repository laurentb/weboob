# -*- coding: utf-8 -*-

# Copyright(C) 2014       Simon Murail
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
from lxml.etree import XPath

from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Investment
from weboob.browser.filters.standard import CleanDecimal


_el_to_string = XPath('string()')

def el_to_string(el):
    return unicode(_el_to_string(el))


class IsinMixin(object):
    def get_isin(self, s):
        mobj = self._re_isin.search(s)
        if mobj:
            return mobj.group(1)


class AccountInvestment(IsinMixin, Page):
    _re_isin = re.compile(r'isin=(\w+)')
    _tr_list = XPath('//div[@id="content-gauche"]//table[@class="list"]/tbody/tr')
    _td_list = XPath('./td')
    _link = XPath('./td[1]/a/@href')

    def get_investment(self):
        Decimal = CleanDecimal(replace_dots=True).filter

        for tr in self._tr_list(self.document):
            cells = list(el_to_string(td) for td in self._td_list(tr))
            link = unicode(self._link(tr)[0])

            '''

            Boursorama table cells
            ----------------------

            0. Fonds
            1. Date de valeur
            2. Valeur de part
            3. Nombre de parts
            4. Contre valeur
            5. Prix revient
            6. +/- value en €*
            7. +/- value en %*

            Investment model
            ----------------

            label =       StringField('Label of stocks')
            code =        StringField('Identifier of the stock (ISIN code)')
            description = StringField('Short description of the stock')
            quantity =    IntField('Quantity of stocks')
            unitprice =   DecimalField('Buy price of one stock')
            unitvalue =   DecimalField('Current value of one stock')
            valuation =   DecimalField('Total current valuation of the Investment')
            diff =        DecimalField('Difference between the buy cost and the current valuation')

            '''

            inv = Investment()
            isin = self.get_isin(link)

            if isin:
                inv.id = inv.code = isin
            inv.label = cells[0]
            inv.quantity = Decimal(cells[3])
            inv.valuation = Decimal(cells[4])
            inv.unitprice = Decimal(cells[5])
            inv.unitvalue = Decimal(cells[2])
            inv.diff = Decimal(cells[6])

            inv._detail_url = link if '/cours.phtml' in link else None

            yield inv


class InvestmentDetail(IsinMixin, Page):
    _re_isin = re.compile('(\w+)')
    _isin = XPath('//h2[@class and contains(concat(" ", normalize-space(@class), " "), " fv-isin ")]')
    _description = XPath('//p[@class="taj"]')

    def get_investment_detail(self, inv):
        subtitle = el_to_string(self._isin(self.document)[0])

        inv.id = inv.code = self.get_isin(subtitle)
        inv.description = el_to_string(self._description(self.document)[0]).strip()

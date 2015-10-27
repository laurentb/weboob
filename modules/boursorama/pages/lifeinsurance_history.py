# -*- coding: utf-8 -*-

# Copyright(C) 2015       Baptiste Delpey
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


from weboob.deprecated.browser import Page
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.bank import Investment
from weboob.browser.filters.standard import CleanDecimal, Date
from weboob.capabilities import NotAvailable


Decimal = CleanDecimal(replace_dots=True).filter
Date = Date().filter


class LifeInsuranceHistory(Page):
    def get_operations(self):
        for tr in self.document.xpath('//div[@class="block no-hd"]//table[@class="list"]/tbody/tr'):
            tds = tr.xpath('./td')

            date = self.parser.tocleanstring(tds[0])
            label = self.parser.tocleanstring(tds[1])
            amount = self.parser.tocleanstring(tds[2])
            _id = 0

            operation = FrenchTransaction(_id)
            operation.parse(date=date, raw=label)
            operation.set_amount(amount)

            if tds[0].xpath('./a'):
                operation.investments = self.get_investments(tds[0].xpath('./a')[0].attrib['href']) or NotAvailable

            yield operation

    def get_next_url(self):
        selected = self.document.xpath('//div[@class="pagination"]/ul/li[@class="selected active"]/a')
        link = self.document.xpath('//div[@class="pagination"]/ul/li[@class="next"]/a')
        if selected and link:
            selected = selected[0].attrib['href']
            link = link[0].attrib['href']

        if selected != link:
            return link

    def get_investments(self, link):
        invests = []
        doc = self.browser.get_document(self.browser.openurl(link))
        for table in doc.xpath('//div[@class="block" and not(@style)]//table'):
            for tr in table.xpath('./tr')[1:]:
                tds = tr.xpath('./td')
                inv = Investment()
                inv.label = self.parser.tocleanstring(tds[0])
                inv.vdate = Date(self.parser.tocleanstring(tds[1]))
                inv.unitprice = Decimal(tds[2])
                inv.quantity = Decimal(tds[3])
                inv.valuation = Decimal(tds[4])
                invests.append(inv)
        return invests

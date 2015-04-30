# -*- coding: utf-8 -*-

# Copyright(C) 2009-2012  Romain Bignon
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
from decimal import Decimal
from xml.etree import ElementTree

from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.base import NotAvailable


def clean_text(el):
    text = ElementTree.tostring(el, 'utf-8', 'text').decode('utf-8')
    return re.sub(ur'[\s\xa0]+', u' ', text).strip()


def clean_cells(cells):
    return list(map(clean_text, cells))


def clean_amount(amount):
    return Decimal(FrenchTransaction.clean_amount(amount)) if amount else NotAvailable


def clean_amounts(amounts):
    return list(map(clean_amount, amounts))


class AccountMarketInvestment(Page):
    def iter_investment(self):
        table = self.document.xpath('//table[@align="center"]')[4]
        rows = table.xpath('.//tr[@class="hdoc1"]')
        for tr in rows:
            cells = clean_cells(tr.findall('td'))
            cells[2:] = clean_amounts(cells[2:])

            inv = Investment()
            inv.label, _, inv.quantity, inv.unitvalue, inv.valuation = cells

            tr2 = tr.xpath('./following-sibling::tr')[0]
            tr2td = tr2.findall('td')[1]

            inv.id = inv.code = clean_text(tr2.xpath('.//a')[0])
            inv.unitprice = clean_amount(tr2td.xpath('.//td[@class="hdotc1nb"]')[0].text)

            inv.description = u''
            inv.diff = inv.quantity * inv.unitprice - inv.valuation

            yield inv


class AccountLifeInsuranceInvestment(Page):
    def iter_investment(self):
        rows = self.document.xpath('//table[@id="mefav_repartition_supports_BPF"]//tr') or \
               self.document.xpath('//tbody[@id="mefav_repartition_supports"]//tr')
        for tr in rows:
            cells = clean_cells(tr.findall('td'))
            cells[3:] = clean_amounts(cells[3:])

            inv = Investment()
            inv.label, _, inv.code, inv.quantity, inv.unitvalue, inv.valuation, _ = cells

            if inv.code:
                inv.id = inv.code
            if not inv.unitvalue:
                # XXX Fonds eu Euros
                inv.code = u'XX' + re.sub(ur'[^A-Za-z0-9]', u'', inv.label).upper()
            inv.description = u''

            yield inv

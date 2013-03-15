# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from decimal import Decimal
import re

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.capabilities import NotAvailable
from weboob.capabilities.pricecomparison import Product, Shop, Price


__all__ = ['IndexPage', 'ComparisonResultsPage', 'ShopInfoPage']


class IndexPage(BasePage):
    def iter_products(self):
        for li in self.parser.select(self.document.getroot(), 'div#choix_carbu ul li'):
            input = li.find('input')
            label = li.find('label')

            product = Product(input.attrib['value'])
            product.name = unicode(label.text.strip())

            if '&' in product.name:
                # "E10 & SP95" produces a non-supported table.
                continue

            yield product


class ComparisonResultsPage(BasePage):
    def get_product_name(self):
        try:
            div = self.parser.select(self.document.getroot(), 'div#moins_plus_ariane', 1)
        except BrokenPageError:
            return NotAvailable
        else:
            m = re.match('Carburant : ([\w\-]+) | .*', div.text)
            return m.group(1)

    def iter_results(self, product=None):
        price = None
        product.name = self.get_product_name()
        for tr in self.document.getroot().cssselect('table#tab_resultat tr'):
            if tr.attrib.get('id', '').startswith('pdv'):
                price = Price('%s.%s' % (product.id, tr.attrib['id'][3:]))

                price.product = product

                tds = tr.findall('td')
                price.cost = Decimal(tds[4].text.replace(',', '.'))
                price.currency = u'€'

                shop = Shop(price.id)
                shop.name = unicode(tds[2].text.strip())
                shop.location = unicode(tds[0].text.strip())

                price.shop = shop
                price.set_empty_fields(NotAvailable)
                yield price


class ShopInfoPage(BasePage):
    def get_info(self):
        return self.parser.tostring(self.parser.select(self.document.getroot(), 'div.colg', 1))

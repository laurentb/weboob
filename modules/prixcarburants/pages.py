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

from weboob.deprecated.browser import Page
from weboob.capabilities import NotAvailable
from weboob.capabilities.pricecomparison import Product, Shop, Price


class IndexPage(Page):

    def get_token(self):
        input = self.parser.select(self.document.getroot(), 'div#localisation input#recherche_recherchertype__token', 1)
        return input.attrib['value']

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


class ComparisonResultsPage(Page):
    def get_product_name(self):
        th = self.document.getroot().cssselect('table#tab_resultat tr th')
        if th and len(th) == 9:
            return u'%s' % th[5].find('a').text

    def iter_results(self, product=None):
        price = None
        product.name = self.get_product_name()
        for tr in self.document.getroot().cssselect('table#tab_resultat tr'):
            tds = self.parser.select(tr, 'td')
            if tds and len(tds) == 9 and product is not None:
                price = Price('%s.%s' % (product.id, tr.attrib['id']))

                price.product = product

                price.cost = Decimal(tds[5].text.replace(',', '.'))
                price.currency = u'€'

                shop = Shop(price.id)
                shop.name = unicode(tds[3].text.strip())
                shop.location = unicode(tds[2].text.strip())

                price.shop = shop
                price.set_empty_fields(NotAvailable)
                yield price


class ShopInfoPage(Page):
    def get_info(self):
        return self.parser.tostring(self.parser.select(self.document.getroot(), 'div.infos', 1))

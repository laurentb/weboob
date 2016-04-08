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

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.capabilities.pricecomparison import CapPriceComparison, Price, Product, PriceNotFound
from weboob.capabilities.base import find_object

from .browser import PrixCarburantsBrowser


__all__ = ['PrixCarburantsModule']


class PrixCarburantsModule(Module, CapPriceComparison):
    NAME = 'prixcarburants'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.2'
    DESCRIPTION = 'French governement website to compare fuel prices'
    LICENSE = 'AGPLv3+'
    BROWSER = PrixCarburantsBrowser
    CONFIG = BackendConfig(Value('zipcode', label='Zipcode', regexp='\d+'))

    def search_products(self, pattern=None):
        for product in self.browser.iter_products():
            if pattern is None or pattern.lower() in product.name.lower():
                yield product

    def iter_prices(self, products):
        product = [product for product in products if product.backend == self.name]
        if product:
            return self.browser.iter_prices(self.config['zipcode'].get(), product[0])

    def get_price(self, id, price=None):
        product = Product(id.split('.')[0])
        product.backend = self.name

        price = find_object(self.iter_prices([product]), id=id, error=PriceNotFound)
        price.shop.info = self.browser.get_shop_info(price.id.split('.', 2)[-1])
        return price

    def fill_price(self, price, fields):
        return self.get_price(price.id, price)

    OBJECTS = {Price: fill_price, }

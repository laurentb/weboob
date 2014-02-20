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

import re
from weboob.capabilities.pricecomparison import ICapPriceComparison, Price, Product
from weboob.tools.backend import BaseBackend, BackendConfig
#from weboob.tools.value import Value

from .browser import LaCentraleBrowser


__all__ = ['LaCentraleBackend']


class LaCentraleBackend(BaseBackend, ICapPriceComparison):
    NAME = 'lacentrale'
    MAINTAINER = u'Vicnet'
    EMAIL = 'vicnet@weboob.org'
    VERSION = '0.h'
    DESCRIPTION = 'Vehicule prices at LaCentrale.fr'
    LICENSE = 'AGPLv3+'
#    CONFIG = BackendConfig(Value('zipcode',                 label='Zipcode', regexp='\d+'))
    BROWSER = LaCentraleBrowser

    # inherited from ICapPriceComparison
    def search_products(self, patternString=None):
        # convert pattern to criteria
        criteria = { }
        patterns = []
        if patternString:
            patterns = patternString.split(',')
        for pattern in patterns:
            pattern = pattern.lower()
            if u'€' in pattern:
                criteria['maxprice'] = pattern[:pattern.find(u'€')].strip()
            if u'km' in pattern:
                criteria['maxdist'] = pattern[:pattern.find(u'km')].strip()
            if u'p' in pattern[-1]: # last char = p
                criteria['nbdoors'] = pattern[:pattern.find(u'p')].strip()
            if u'cit' in pattern:
                criteria['urban'] = 'citadine&SS_CATEGORIE=40'
            if u'dep' in pattern:
                criteria['dept'] = re.findall('\d+',pattern)[0]
            if u'pro' in pattern:
                criteria['origin'] = 1
            if u'part' in pattern:
                criteria['origin'] = 0
            #print criteria
        # browse product
        with self.browser:
            for product in self.browser.iter_products(criteria):
                yield product

    def iter_prices(self, product):
        # inherited from ICapPriceComparison
        with self.browser:
            return self.browser.iter_prices(product)

#    def get_price(self, id):
		# inherited from ICapPriceComparison
#        with self.browser:
#            if isinstance(id, Price):
#                price = id
#            else:
#                p_id, s_id = id.split('.', 2)
#                product = Product(p_id)
#                for price in self.iter_prices(product):
#                    if price.id == id:
#                        break
#                else:
#                    return None

#            price.shop.info = self.browser.get_shop_info(price.id.split('.', 2)[-1])
#            return price

 #   def fill_price(self, price, fields):
 #       return self.get_price(price)

 #   OBJECTS = {Price: fill_price, }

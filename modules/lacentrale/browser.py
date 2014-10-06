# -*- coding: utf-8 -*-

# Copyright(C) 2014 Vicnet
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

from weboob.deprecated.browser import Browser

from .pages import MainPage, ListingAutoPage, AnnoncePage


__all__ = ['LaCentraleBrowser']


# I manage urls and page location, then trasnfert to page
class LaCentraleBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.lacentrale.fr'
    ENCODING = 'windows-1252'
    PAGES = {'http://www.lacentrale.fr/': MainPage,
             'http://www.lacentrale.fr/listing_auto.php?.*': ListingAutoPage,
             'http://www.lacentrale.fr/auto-occasion-annonce-.*': AnnoncePage,
             }

    def iter_products(self, criteria):
        if not self.is_on_page(MainPage):
            self.location('/')
        assert self.is_on_page(MainPage)
        return self.page.iter_products(criteria)

    def _buildUrl(self, product, request, criteria):
        if criteria in product._criteria:
            return '&' + request.format(product._criteria.get(criteria))
        return ''

    def iter_prices(self, product):
        # convert product criteria to url encoding
        if not self.is_on_page(ListingAutoPage):
            #TODO use urllib.urlencode(data) ?
            url = '/listing_auto.php?num=1&witchSearch=0'
            url += self._buildUrl(product, 'Citadine={}', 'urban')
            url += self._buildUrl(product, 'prix_maxi={}', 'maxprice')
            url += self._buildUrl(product, 'km_maxi={}', 'maxdist')
            url += self._buildUrl(product, 'nbportes=%3D{}', 'nbdoors')
            url += self._buildUrl(product, 'cp={}', 'dept')
            url += self._buildUrl(product, 'origine={}', 'origin')
            #print url
            self.location(url)

        assert self.is_on_page(ListingAutoPage)

        numpage = 1
        while True:
            # parse the current page
            for price in self.page.iter_prices(product, numpage):
                yield price

            # check if next page
            numpage = self.page.get_next()
            if not numpage:
                break
            url = re.sub('num=(\d+)', 'num={}'.format(numpage), url)
            self.location(url)
            assert self.is_on_page(ListingAutoPage)

    def get_price(self, id):
        #/auto-occasion-annonce-23440064.html
        self.location('/auto-occasion-annonce-'+id+'.html')
        assert self.is_on_page(AnnoncePage)
        return self.page.get_price(id)

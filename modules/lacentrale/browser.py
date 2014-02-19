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


import urllib
import re

from weboob.tools.browser import BaseBrowser

from .pages import MainPage, ListingAutoPage


__all__ = ['LaCentraleBrowser']


class LaCentraleBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.lacentrale.fr'
    ENCODING = 'windows-1252'
    PAGES = {
         'http://www.lacentrale.fr/': MainPage,
         'http://www.lacentrale.fr/listing_auto.php?.*': ListingAutoPage,
        }
#http://www.lacentrale.fr/listing_auto.php?witchSearch=0&SS_CATEGORIE=40&mo_comm=&Citadine=citadine=&km_maxi=120000&annee2=&conso=&co2=&opt=&version=&transmission=&couleur=&nbportes=%3D5&photo=&new_annonce=&cp=31&origine=1

    def iter_products(self, criteria):
        if not self.is_on_page(MainPage):
            self.location('/')
        assert self.is_on_page(MainPage)
        return self.page.iter_products(criteria)

    def buildUrl(self, product, request, criteria):
        if product._criteria.has_key(criteria):
            return '&' + request.format(product._criteria.get(criteria))
        return ''

    def iter_prices(self, product):
        if not self.is_on_page(ListingAutoPage):
            url = '/listing_auto.php?num=1&witchSearch=0'
            url += self.buildUrl(product, 'Citadine={}','urban')
            url += self.buildUrl(product, 'prix_maxi={}','maxprice')
            url += self.buildUrl(product, 'km_maxi={}','maxdist')
            url += self.buildUrl(product, 'nbportes=%3D{}','nbdoors')
            url += self.buildUrl(product, 'cp={}','dept')
            url += self.buildUrl(product, 'origin={}','origin')
            #print url
            self.location(url)

        assert self.is_on_page(ListingAutoPage)

        numpage = 1
        while True:
            # parse the current page
            for price in self.page.iter_prices(numpage):
                yield price

            # check if next page
            numpage = self.page.get_next()
            if not numpage:
                break
            url = re.sub('num=(\d+)','num={}'.format(numpage),url)
            self.location(url)
            assert self.is_on_page(ListingAutoPage)

#    def iter_prices(self, zipcode, product):
#        data = {'aff_param_0_0':            '',
#                'aff_param_0_1':            'les points de vente',
#                'aff_param_0_3':            zipcode,
#                'changeNbPerPage':          'off',
#                'toDelete':                 -1,
#               }
#        self.location('/index.php?module=dbgestion&action=search', urllib.urlencode(data))
#
#        assert self.is_on_page(ComparisonResultsPage)
#        return self.page.iter_results(product)
#
#    def get_shop_info(self, id):
#        data = {'pdv_id': id,
#                'module':   'dbgestion',
#                'action':   'getPopupInfo'}
#        self.location('/index.php?module=dbgestion&action=getPopupInfo', urllib.urlencode(data))
#
#        assert self.is_on_page(ShopInfoPage)
#        return self.page.get_info()

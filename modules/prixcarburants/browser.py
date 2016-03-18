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

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.base import UserError
from .pages import IndexPage, ComparisonResultsPage, ShopInfoPage


__all__ = ['PrixCarburantsBrowser']


class PrixCarburantsBrowser(PagesBrowser):
    BASEURL = 'http://www.prix-carburants.economie.gouv.fr'

    TOKEN = None

    result_page = URL('/recherche/', ComparisonResultsPage)
    shop_page = URL('/itineraire/infos/(?P<_id>\d+)', ShopInfoPage)
    index_page = URL('/', IndexPage)

    def iter_products(self):
        return self.index_page.go().iter_products()

    def get_token(self):
        self.TOKEN = self.index_page.stay_or_go().get_token()

    def iter_prices(self, zipcode, product):
        if self.TOKEN is None:
            self.get_token()

        data = {
            '_recherche_recherchertype[localisation]': '%s' % zipcode,
            '_recherche_recherchertype[choix_carbu]': '%s' % product.id,
            '_recherche_recherchertype[_token]': '%s' % self.TOKEN, }

        self.index_page.go(data=data)

        if not self.result_page.is_here():
            raise UserError('Bad zip or product')

        if not product.name:
            product.name = self.page.get_product_name()

        return self.page.iter_results(product=product)

    def get_shop_info(self, id):
        return self.shop_page.go(_id=id).get_info()

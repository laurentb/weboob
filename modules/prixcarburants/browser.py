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

from weboob.deprecated.browser import Browser

from .pages import IndexPage, ComparisonResultsPage, ShopInfoPage


__all__ = ['PrixCarburantsBrowser']


class PrixCarburantsBrowser(Browser):
    TOKEN = None
    PROTOCOL = 'http'
    DOMAIN = 'www.prix-carburants.economie.gouv.fr'
    ENCODING = 'iso-8859-15'
    PAGES = {
        'http://www.prix-carburants.economie.gouv.fr': IndexPage,
        'http://www.prix-carburants.economie.gouv.fr/recherche/': ComparisonResultsPage,
        'http://www.prix-carburants.economie.gouv.fr/itineraire/infos/\d+': ShopInfoPage, }

    def iter_products(self):
        if not self.is_on_page(IndexPage):
            self.location("%s://%s" % (self.PROTOCOL, self.DOMAIN))

        assert self.is_on_page(IndexPage)
        return self.page.iter_products()

    def get_token(self):
        if not self.is_on_page(IndexPage):
            self.location("%s://%s" % (self.PROTOCOL, self.DOMAIN))

        assert self.is_on_page(IndexPage)
        self.TOKEN = self.page.get_token()

    def iter_prices(self, zipcode, product):
        if self.TOKEN is None:
            self.get_token()

        data = {
            '_recherche_recherchertype[localisation]': '%s' % zipcode,
            '_recherche_recherchertype[choix_carbu]': '%s' % product.id,
            '_recherche_recherchertype[_token]': '%s' % self.TOKEN, }

        self.location('%s://%s' % (self.PROTOCOL, self.DOMAIN), urllib.urlencode(data))
        assert self.is_on_page(ComparisonResultsPage)
        return self.page.iter_results(product)

    def get_shop_info(self, id):
        self.location('%s://%s/itineraire/infos/%s' % (self.PROTOCOL, self.DOMAIN, id))
        assert self.is_on_page(ShopInfoPage)
        return self.page.get_info()

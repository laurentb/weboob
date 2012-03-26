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

from weboob.tools.browser import BaseBrowser

from .pages import IndexPage, ComparisonResultsPage, ShopInfoPage


__all__ = ['PrixCarburantsBrowser']


class PrixCarburantsBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.prix-carburants.economie.gouv.fr'
    ENCODING = 'iso-8859-15'
    PAGES = {
         'http://www\.prix-carburants\.economie\.gouv\.fr/index\.php': IndexPage,
         'http://www\.prix-carburants\.economie\.gouv\.fr/index\.php\?module=dbgestion\&action=search': ComparisonResultsPage,
         'http://www\.prix-carburants\.economie\.gouv\.fr/index\.php\?module=dbgestion\&action=getPopupInfo': ShopInfoPage,
        }

    def iter_products(self):
        if not self.is_on_page(IndexPage):
            self.location('/index.php')

        assert self.is_on_page(IndexPage)
        return self.page.iter_products()

    def iter_prices(self, zipcode, product):
        data = {'aff_param_0_0':            '',
                'aff_param_0_1':            'les points de vente',
                'aff_param_0_2':            '',
                'aff_param_0_3':            zipcode,
                'changeNbPerPage':          'off',
                'col*param*pdv_brand':      'Marque',
                'col*param*pdv_city':       'Commune',
                'col*param*pdv_name':       'Nom du point de vente',
                'col*param*pdv_pop':        '',
                'col*param*price_fuel_%s' % product.id:   'GPL',
                'col*param*price_lmdate_%s' % product.id: 'Mise a jour GPL',
                'critere_contrainte':       'letters',
                'critere_info':             'pdv_city*0',
                'critere_txt':              '',
                'flag_contrainte':          'off',
                'index_contrainte':         0,
                'modeaffichage':            'list',
                'nb_search_per_page':       100,
                'orderBy':                  'price_fuel_%s' % product.id,
                'orderType':                'ASC',
                'req_param_0_0':            '',
                'req_param_0_1':            'pdv_zipcode',
                'req_param_0_2':            'ILIKE',
                'req_param_0_3':            '%s%%' % zipcode,
                'seeFuel':                  product.id,
                'thisPageLetter':           'Tous',
                'thisPageNumber':           1,
                'toDelete':                 -1,
               }
        self.location('/index.php?module=dbgestion&action=search', urllib.urlencode(data))

        assert self.is_on_page(ComparisonResultsPage)
        return self.page.iter_results(product)

    def get_shop_info(self, id):
        data = {'pdv_id': id,
                'module':   'dbgestion',
                'action':   'getPopupInfo'}
        self.location('/index.php?module=dbgestion&action=getPopupInfo', urllib.urlencode(data))

        assert self.is_on_page(ShopInfoPage)
        return self.page.get_info()

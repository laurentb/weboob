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


import json

from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BaseBrowser

from .pages import SearchResultsPage, HousingPage, HousingPhotosPage


__all__ = ['SeLogerBrowser']


class SeLogerBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.seloger.com'
    ENCODING = 'utf-8'
    PAGES = {
         'http://www.seloger.com/(pre)?recherche.htm.*': SearchResultsPage,
         'http://www.seloger.com/annonces.htm.*': SearchResultsPage,
         'http://www.seloger.com/annonces/.*': HousingPage,
         'http://www.seloger.com/\d+/incl_detail_annonce_load_diapo_new.htm': HousingPhotosPage,
        }

    def search_geo(self, pattern):
        fp = self.openurl(self.buildurl('http://www.seloger.com/js,ajax,villequery_v3.htm', ville=pattern, mode=1))
        return json.load(fp)

    def search_housings(self, cities, area_min, area_max, cost_min, cost_max):
        data = {'ci':            ','.join(cities),
                'idtt':          1, #location
                'idtypebien':    1, #appart
                'org':           'advanced_search',
                'px_loyermax':   cost_max or '',
                'px_loyermin':   cost_min or '',
                'surfacemax':    area_max or '',
                'surfacemin':    area_min or '',
               }

        self.location(self.buildurl('/prerecherche.htm', **data))
        assert self.is_on_page(SearchResultsPage)

        return self.page.iter_housings()

    def get_housing(self, id, obj=None):
        self.location('/%d/detail_new.htm' % int(id))

        assert self.is_on_page(HousingPage)
        housing = self.page.get_housing(obj)

        self.location('/%d/incl_detail_annonce_load_diapo_new.htm' % int(id))
        housing.photos = list(self.page.iter_photos()) or NotAvailable

        return housing

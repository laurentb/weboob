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

from weboob.tools.browser import BaseBrowser

from .pages import SearchResultsPage, HousingPage


__all__ = ['SeLogerBrowser']


class SeLogerBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.seloger.com'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['android']
    PAGES = {
         'http://ws.seloger.com/search.xml.*': SearchResultsPage,
         'http://ws.seloger.com/annonceDetail.xml\?idAnnonce=(\d+)(&noAudiotel=\d)?': HousingPage,
        }

    def search_geo(self, pattern):
        fp = self.openurl(self.buildurl('http://www.seloger.com/js,ajax,villequery_v3.htm', ville=pattern, mode=1))
        return json.load(fp)

    def search_housings(self, cities, nb_rooms, area_min, area_max, cost_min, cost_max):
        data = {'ci':            ','.join(cities),
                'idtt':          1, #location
                'idtypebien':    1, #appart
                'org':           'advanced_search',
                'px_loyermax':   cost_max or '',
                'px_loyermin':   cost_min or '',
                'surfacemax':    area_max or '',
                'surfacemin':    area_min or '',
                'tri':           'd_dt_crea',
               }

        if nb_rooms:
            data['nb_pieces'] = nb_rooms

        self.location(self.buildurl('http://ws.seloger.com/search.xml', **data))

        while 1:
            assert self.is_on_page(SearchResultsPage)

            for housing in self.page.iter_housings():
                yield housing

            url = self.page.next_page_url()
            if url is None:
                return

            self.location(url)

    def get_housing(self, id, obj=None):
        self.location(self.buildurl('http://ws.seloger.com/annonceDetail.xml', idAnnonce=id, noAudiotel=1))

        assert self.is_on_page(HousingPage)
        housing = self.page.get_housing(obj)

        return housing

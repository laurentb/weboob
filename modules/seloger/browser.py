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


from weboob.tools.json import json

from weboob.tools.browser import Browser
from weboob.capabilities.housing import Query

from .pages import SearchResultsPage, HousingPage


__all__ = ['SeLogerBrowser']


class SeLogerBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.seloger.com'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['android']
    PAGES = {
         'http://ws.seloger.com/search.xml.*': SearchResultsPage,
         'http://ws.seloger.com/annonceDetail.xml\?idAnnonce=(\d+)(&noAudiotel=\d)?': HousingPage,
        }

    def search_geo(self, pattern):
        fp = self.openurl(self.buildurl('http://www.seloger.com/js,ajax,villequery_v3.htm', ville=pattern.encode('utf-8'), mode=1))
        return json.load(fp)

    TYPES = {Query.TYPE_RENT: 1,
             Query.TYPE_SALE: 2
            }

    def search_housings(self, type, cities, nb_rooms, area_min, area_max, cost_min, cost_max):
        data = {'ci':            ','.join(cities),
                'idtt':          self.TYPES.get(type, 1),
                'idtypebien':    1, #appart
                'org':           'advanced_search',
                'surfacemax':    area_max or '',
                'surfacemin':    area_min or '',
                'tri':           'd_dt_crea',
               }

        if type == Query.TYPE_SALE:
            data['pxmax'] = cost_max or ''
            data['pxmin'] = cost_min or ''
        else:
            data['px_loyermax'] = cost_max or ''
            data['px_loyermin'] = cost_min or ''

        if nb_rooms:
            data['nb_pieces'] = nb_rooms

        self.location(self.buildurl('http://ws.seloger.com/search.xml', **data))

        while True:
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

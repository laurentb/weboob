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

from weboob.capabilities.housing import TypeNotSupported, POSTS_TYPES, ADVERT_TYPES
from weboob.tools.compat import urlencode

from weboob.browser import PagesBrowser, URL
from .pages import SearchResultsPage, HousingPage, CitiesPage
from weboob.browser.profiles import Android

from .constants import TYPES, RET

__all__ = ['SeLogerBrowser']


class SeLogerBrowser(PagesBrowser):
    BASEURL = 'http://www.seloger.com'
    PROFILE = Android()
    cities = URL('https://autocomplete.svc.groupe-seloger.com/auto/complete/0/Ville/6\?text=(?P<pattern>.*)', CitiesPage)
    search = URL('http://ws.seloger.com/search.xml\?(?P<request>.*)', SearchResultsPage)
    housing = URL('http://ws.seloger.com/annonceDetail.xml\?idAnnonce=(?P<_id>\d+)&noAudiotel=(?P<noAudiotel>\d)',
                  HousingPage)

    def search_geo(self, pattern):
        return self.cities.open(pattern=pattern).iter_cities()

    def search_housings(self, type, cities, nb_rooms, area_min, area_max,
                        cost_min, cost_max, house_types, advert_types):
        if type not in TYPES:
            raise TypeNotSupported()

        data = {'ci':            ','.join(cities),
                'idtt':          TYPES.get(type, 1),
                'org':           'advanced_search',
                'surfacemax':    area_max or '',
                'surfacemin':    area_min or '',
                'tri':           'd_dt_crea',
                }

        if type == POSTS_TYPES.SALE:
            data['pxmax'] = cost_max or ''
            data['pxmin'] = cost_min or ''
        else:
            data['px_loyermax'] = cost_max or ''
            data['px_loyermin'] = cost_min or ''

        if nb_rooms:
            data['nb_pieces'] = nb_rooms

        ret = []
        for house_type in house_types:
            if house_type in RET:
                ret.append(RET.get(house_type))

        if ret:
            data['idtypebien'] = ','.join(ret)

        if(len(advert_types) == 1 and
           advert_types[0] == ADVERT_TYPES.PROFESSIONAL):
            data['SI_PARTICULIER'] = 0
        elif(len(advert_types) == 1 and
           advert_types[0] == ADVERT_TYPES.PERSONAL):
            data['SI_PARTICULIER'] = 1

        return self.search.go(request=urlencode(data)).iter_housings(
            query_type=type
        )

    def get_housing(self, _id, obj=None):
        return self.housing.go(_id=_id, noAudiotel=1).get_housing(obj=obj)

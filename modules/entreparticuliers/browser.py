# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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
from weboob.capabilities.housing import Query, TypeNotSupported
from weboob.browser import PagesBrowser, URL

from .pages import CitiesPage, SearchPage, HousingPage


class EntreparticuliersBrowser(PagesBrowser):
    BASEURL = 'http://www.entreparticuliers.com'

    cities = URL('/HTTPHandlers/LocalisationsAutocompleteHandler.ashx\?q=(?P<pattern>.*)', CitiesPage)
    form_item = URL('/Default.aspx/GetElementsMoteur')
    search = URL('/default.aspx/CreateSearchParams')
    search_result = URL('/default.aspx/GetAnnonces', SearchPage)
    housing = URL('/default.aspx/GetAnnonceDetail', HousingPage)

    def search_city(self, pattern):
        return self.cities.open(pattern=pattern).iter_cities()

    TYPES = {Query.TYPE_RENT: "1",
             Query.TYPE_SALE: "4"
             }

    RET = {Query.TYPE_RENT: {Query.HOUSE_TYPES.HOUSE: '2',
                             Query.HOUSE_TYPES.APART: '1',
                             Query.HOUSE_TYPES.LAND: '',
                             Query.HOUSE_TYPES.PARKING: '4',
                             Query.HOUSE_TYPES.OTHER: '6'},
           Query.TYPE_SALE: {Query.HOUSE_TYPES.HOUSE: '2',
                             Query.HOUSE_TYPES.APART: '1',
                             Query.HOUSE_TYPES.LAND: '5',
                             Query.HOUSE_TYPES.PARKING: '6',
                             Query.HOUSE_TYPES.OTHER: '9'}
           }

    def search_housings(self, type, cities, nb_rooms, area_min, area_max, cost_min, cost_max, house_types):

        if type not in self.TYPES:
            raise TypeNotSupported

        self.update_header()
        result = self.form_item.open(data="{'rubrique': '%s'}" % self.TYPES.get(type))
        biens = json.loads(json.loads(result.content)['d'])

        for house_type in house_types:
            id_type = self.RET[type].get(house_type, '1')

            data = {}
            data['rubrique'] = self.TYPES.get(type)
            data['ach_id'] = None
            data['FromMoteur'] = "true"

            for bien in biens:
                if bien['Idchoix'] == int(id_type):
                    data['lstSSTbien'] = bien['SsTypebien']
                    data['lstTbien'] = bien['TypeBien']
                    data['Caracteristique'] = bien['Idchoix']

            data['OrigineAlerte'] = "SaveSearchMoteurHome"
            data['pays'] = "fra"
            data['prix_min'] = cost_min if cost_min and cost_min > 0 else None
            data['prix_max'] = cost_max if cost_max and cost_max > 0 else None
            data['lstThemes'] = ""

            min_rooms = nb_rooms if nb_rooms else None
            if not min_rooms:
                data['lstNbPieces'] = 0
            else:
                data['lstNbPieces'] = ','.join('%s' % n for n in range(min_rooms, 6))

            data['lstNbChambres'] = None
            data['surface_min'] = area_min if area_min else None
            # var localisationType = { "all": -1, "ville": 5, "region": 2, "departement": 4, "pays": 1, "regionUsuelle": 3 };
            data['localisationType'] = 5
            data['reference'] = ''
            data['rayon'] = 0
            data['localisation_id_rayon'] = None
            data['lstLocalisationId'] = ','.join(cities)
            data['photos'] = 0
            data['colocation'] = ''
            data['meuble'] = ''
            data['pageNumber'] = 1
            data['order_by'] = 1
            data['sort_order'] = 1
            data['top'] = 25
            data['SaveSearch'] = "false"
            data['EmailUser'] = ""
            data['GSMUser'] = ""

            self.search.go(data="{'p_SearchParams':'%s', 'forcealerte':'0'}" % json.dumps(data))

            data = '{pageIndex: 1,source:"undefined"}'
            for item in self.search_result.go(data=data).iter_housings():
                yield item

    def get_housing(self, _id, obj=None):
        self.update_header()
        splitted_id = _id.split('#')
        data = '{idannonce: %s,source:"%s",rubrique:%s}' % (splitted_id[0], splitted_id[2], splitted_id[1])
        obj = self.housing.go(data=data).get_housing(obj=obj)
        obj.id = _id
        return obj

    def update_header(self):
        self.session.headers.update({"X-Requested-With": "XMLHttpRequest",
                                     "Content-Type": "application/json; charset=utf-8",
                                     "Accept": "application/json, text/javascript, */*; q=0.01"})

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
from weboob.capabilities.housing import Query
from weboob.browser import PagesBrowser, URL

from .pages import CitiesPage, SearchPage, HousingPage


class EntreparticuliersBrowser(PagesBrowser):
    BASEURL = 'http://www.entreparticuliers.com'

    cities = URL('/HTTPHandlers/LocalisationsAutocompleteHandler.ashx\?q=(?P<pattern>.*)', CitiesPage)
    search = URL('/Default.aspx/CreateSearchParams')
    form_item = URL('/Default.aspx/GetElementsMoteur')
    search_result = URL('/annonces-immobilieres/vente/resultats-de-recherche-ergo', SearchPage)
    housing = URL('/(?P<_id>.*).html', HousingPage)

    def search_city(self, pattern):
        return self.cities.open(pattern=pattern).iter_cities()

    TYPES = {Query.TYPE_RENT: 1,
             Query.TYPE_SALE: 4
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
        referer = "http://www.entreparticuliers.com/annonces-immobilieres/vente/resultats-de-recherche-ergo"
        self.session.headers.update({"X-Requested-With": "XMLHttpRequest",
                                     "Referer": referer,
                                     "Content-Type": "application/json; charset=utf-8",
                                     "Accept": "application/json, text/javascript, */*; q=0.01"})

        result = self.form_item.open(data="{'rubrique': '%s'}" % self.TYPES.get(type))
        biens = json.loads(json.loads(result.content)['d'])

        for house_type in house_types:
            id_type = self.RET[type].get(house_type, '1')

            data = {}
            data['rubrique'] = self.TYPES.get(type)
            data['ach_id'] = None
            data['FromMoteur'] = True

            for bien in biens:
                if bien['Idchoix'] == int(id_type):
                    data['lstSSTbien'] = bien['SsTypebien']
                    data['lstTbien'] = u'%s' % bien['TypeBien']
                    data['Caracteristique'] = bien['Idchoix']

            data['OrigineAlerte'] = "SaveSearchMoteurHome"
            data['pays'] = "fra"
            data['prix_min'] = cost_min if cost_min and cost_min > 0 else None
            data['prix_max'] = cost_max if cost_max and cost_max > 0 else None
            data['lstThemes'] = ""

            min_rooms = nb_rooms if nb_rooms else None
            max_rooms = 5 if min_rooms else None
            if not min_rooms:
                data['lstNbPieces'] = u'0'
            else:
                data['lstNbPieces'] = ','.join('%s' % n for n in range(min_rooms, 6))

            data['Neuf'] = False
            data['EnCours'] = False
            data['IsMarket'] = None
            data['Kilometrage'] = 0
            data['VehiculeAnnee'] = 0
            data['idalerte'] = 0
            data['questionnaire'] = False
            data['Criteres_supplementaires'] = None
            data['financement'] = None
            data['Keyword'] = None
            data['categorielabel'] = None
            data['souscategorielabel'] = None
            data['lstLocalisationIdExtended'] = None
            data['IsVilleMereUniqueSearch'] = False
            data['titre_alerte'] = None
            data['nb_annonces'] = 0
            data['extended_nb_annonces'] = 0
            data['vitrine'] = None
            data['Capacite'] = None
            data['CapaciteMin'] = None
            data['CapaciteMax'] = None
            data['SmsSend'] = False
            data['lstCategorie'] = None
            data['lstNbChambres'] = None
            data['surface_min'] = area_min if area_min else None
            # var modes = { "all": -1, "ville": 5, "region": 2, "departement": 4, "pays": 1, "regionUsuelle": 3 };
            data['localisationType'] = 5
            data['reference'] = ''
            data['nbpiecesMin'] = min_rooms
            data['nbpiecesMax'] = max_rooms
            data['rayon'] = 0
            data['localisation_id_rayon'] = None
            data['listLocalisationExclues'] = None
            data['lstLocalisationIdRayon'] = None
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

            self.search.go(data="{'p_SearchParams':'%s'}" % json.dumps(data))

            for item in self.search_result.go().iter_housings():
                yield item

    def get_housing(self, _id, obj=None):
        return self.housing.go(_id=_id).get_housing(obj=obj)

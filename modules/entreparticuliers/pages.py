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

from decimal import Decimal
from datetime import datetime

from weboob.browser.pages import JsonPage, XMLPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format, Regexp
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.housing import Housing, HousingPhoto, City


class CitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        class item(ItemElement):
            klass = City

            def condition(self):
                return Dict('id', default=None)(self) and\
                    Dict('localisationType')(self) == u'ville'

            obj_id = Dict('id')
            obj_name = Dict('libelle')


class EntreParticuliersXMLPage(XMLPage):
    ENCODING = 'utf-8'

    def build_doc(self, content):
        from weboob.tools.json import json
        json_content = json.loads(content)
        return super(EntreParticuliersXMLPage, self).build_doc(json_content.get('d').encode(self.ENCODING))


class SearchPage(EntreParticuliersXMLPage):
    @method
    class iter_housings(ListElement):
        item_xpath = '//AnnoncePresentation'

        class item(ItemElement):
            klass = Housing

            obj_id = Format('%s#%s#%s',
                            CleanText('./Idannonce'),
                            CleanText('./Rubrique'),
                            CleanText('./Source'))
            obj_title = CleanText('./Titre')
            obj_cost = CleanDecimal('./Prix', default=Decimal(0))
            obj_currency = u'€'
            obj_text = Format('%s / %s', CleanText('Localisation'),
                              CleanText('./MiniINfos'))
            obj_date = datetime.now
            obj_url = CleanText('./LienDetail')


class HousingPage(EntreParticuliersXMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_title = CleanText('//Titre')

        def obj_cost(self):
            cost = CleanDecimal(Regexp(CleanText('//Prix'),
                                       u'(.*)\&euro;.*',
                                       default=None),
                                default=None)(self)
            return cost if cost else CleanDecimal(Regexp(CleanText('//Prix'),
                                                         u'(.*)€'))(self)
        obj_currency = u'€'

        obj_text = CleanText('//Description')
        obj_location = CleanHTML(CleanText('//Localisation'))

        obj_area = CleanDecimal('//SurfaceBien', replace_dots=True)
        obj_phone = CleanText('//Telephone')
        obj_date = datetime.now

        def obj_details(self):
            details = {}
            details[u'Type de bien'] = CleanText('//Tbien')(self)
            details[u'Reference'] = CleanText('(//Reference)[1]')(self)
            details[u'Nb pièces'] = CleanText('//Nbpieces')(self)

            _ener = CleanText('//Energie')(self)
            if _ener:
                details[u'Energie'] = _ener

            _lat = CleanText('//Latitude')(self)
            if _lat:
                details[u'Latitude'] = _lat

            _long = CleanText('//Longitude')(self)
            if _long:
                details[u'Longitude'] = _long

            return details

        def obj_photos(self):
            photos = []
            for i in range(1, CleanDecimal('//NbPhotos')(self) + 1):
                img = CleanText('//LienImage%s' % i, replace=[(u'w=69&h=52', u'w=786&h=481')])(self)
                url = img if img.startswith('http') else u'http://www.entreparticuliers.com%s' % img
                photos.append(HousingPhoto(url))
            return photos

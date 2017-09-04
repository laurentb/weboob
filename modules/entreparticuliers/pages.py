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

import re
from datetime import datetime

from weboob.browser.pages import JsonPage, XMLPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format, Regexp
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.housing import Housing, HousingPhoto, City, UTILITIES
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.capabilities.base import NotAvailable


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
        json_content = json.loads(content).get('d') or u'<Annonce></Annonce>'
        # Fix for invalid encoding sometimes returned by Entreparticuliers
        # see https://stackoverflow.com/questions/3136954/xml-parse-error-on-illegal-character
        json_content = re.sub('&#x1A;', ' ', json_content, flags=re.I)
        return super(EntreParticuliersXMLPage, self).build_doc(json_content.encode(self.ENCODING))


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
            obj_title = CleanText('./MiniINfos')
            obj_location = Format(
                '%s (%s)',
                CleanText('./Localisation'),
                CleanText('./Codepostal')
            )
            obj_cost = CleanDecimal('./Prix', default=NotAvailable)
            obj_currency = u'€'
            obj_utilities = UTILITIES.UNKNOWN
            obj_text = CleanHTML(CleanText('./Description'))
            obj_date = datetime.now

            obj_area = CleanDecimal(
                Regexp(
                    CleanText('./MiniINfos'),
                    u'\s?(\d+)\sm²',
                    default=NotAvailable
                ),
                default=NotAvailable
            )
            obj_rooms = CleanDecimal(
                Regexp(
                    CleanText('./MiniINfos'),
                    '^(\d)+ .*',
                    default=NotAvailable
                ),
                default=NotAvailable
            )
            obj_price_per_meter = PricePerMeterFilter()

            def obj_url(self):
                url = CleanText('./LienDetail')(self)
                if not url.startswith('http'):
                    url = u'http://www.entreparticuliers.com%s' % url
                return url

            def obj_photos(self):
                photos = []
                url = CleanText('./LienImage1')(self)
                if url:
                    if "leboncoin.fr" in url:
                        # For leboncoin, use the real image, not the thumbnail
                        url = url.replace("ad-thumb", "ad-image")

                    photos.append(
                        HousingPhoto(
                            url
                        )
                    )
                return photos


class HousingPage(EntreParticuliersXMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_title = CleanText('//Titre')

        obj_rooms = CleanDecimal('//Nbpieces')

        def obj_cost(self):
            cost = CleanDecimal(Regexp(CleanText('//Prix'),
                                       u'(.*)\&euro;.*',
                                       default=None),
                                default=None)(self)
            return cost if cost else CleanDecimal(Regexp(CleanText('//Prix'),
                                                         u'(.*)€'))(self)
        obj_currency = u'€'
        obj_utilities = UTILITIES.UNKNOWN

        obj_text = CleanText('//Description')
        def obj_location(self):
            return CleanHTML(CleanText('//Localisation'))(self).strip()

        obj_area = CleanDecimal('//SurfaceBien', replace_dots=True,
                                default=NotAvailable)
        obj_price_per_meter = PricePerMeterFilter()
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

        def obj_url(self):
            url = CleanText('./LienDetail')(self)
            if not url.startswith('http'):
                url = u'http://www.entreparticuliers.com%s' % url
            return url

        def obj_photos(self):
            photos = []

            get_url = lambda url: img if img.startswith('http') else u'http://www.entreparticuliers.com%s' % img

            # First image
            img = CleanText('//LienImage',
                            replace=[
                                (u'w=69&h=52', u'w=786&h=481'),
                                (u'ad-thumb', u'ad-large')
                            ],
                            default=None)(self)
            if img:
                photos.append(HousingPhoto(get_url(img)))

            i = 1
            while True:
                # Iterate manually over possible images as the API is
                # completely screwed and could return NbPhotos as being zero
                # although there are some photos.
                img = CleanText('//LienImage%s' % i,
                                replace=[
                                    (u'w=69&h=52', u'w=786&h=481'),
                                    (u'ad-thumb', u'ad-large')
                                ],
                               )(self)
                if not img:
                    break
                photos.append(HousingPhoto(get_url(img)))
                i += 1

            # Filter out duplicates
            seen_photos = []
            filtered_photos = []
            for photo in photos:
                if photo.url not in seen_photos:
                    filtered_photos.append(photo)
                    seen_photos.append(photo.url)

            return filtered_photos

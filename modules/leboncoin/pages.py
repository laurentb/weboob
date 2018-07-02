# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from __future__ import unicode_literals

import requests

from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method, DictElement
from weboob.capabilities.base import Currency as BaseCurrency
from weboob.browser.filters.standard import (CleanText, CleanDecimal, _Filter,
                                             Env, DateTime, Format)
from weboob.browser.filters.json import Dict
from weboob.capabilities.housing import (City, Housing, HousingPhoto,
                                         UTILITIES, ENERGY_CLASS, POSTS_TYPES,
                                         ADVERT_TYPES, HOUSE_TYPES)
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter

from decimal import Decimal
from lxml import etree
import json


class PopDetail(_Filter):
    def __init__(self, name, default=NotAvailable):
        super(PopDetail, self).__init__(default)
        self.name = name

    def __call__(self, item):
        return item.env['details'].pop(self.name, self.default)


class CityListPage(HTMLPage):

    def build_doc(self, content):
        content = super(CityListPage, self).build_doc(content)
        if content.getroot() is not None:
            return content
        return etree.Element("html")

    @method
    class get_cities(ListElement):
        item_xpath = '//li'

        class item(ItemElement):
            klass = City

            obj_id = Format('%s %s',
                            CleanText('./span[has-class("city")]'),
                            CleanText('./span[@class="zipcode"]'))

            obj_name = Format('%s %s',
                              CleanText('./span[has-class("city")]'),
                              CleanText('./span[@class="zipcode"]'))


class HomePage(HTMLPage):
    def __init__(self, *args, **kwargs):
        HTMLPage.__init__(self, *args, **kwargs)

        add_content = CleanText('(//body/script)[3]', replace=[('window.FLUX_STATE = ', '')])(self.doc)

        api_content = CleanText('(//body/script)[2]', replace=[('window.APP_CONFIG = ', '')])(self.doc)

        self.htmldoc = self.doc
        self.api_content = json.loads(api_content)
        self.doc = json.loads(add_content)

    def get_api_key(self):
        return Dict('API/KEY')(self.api_content)


class HousingListPage(JsonPage):

    def __init__(self, *args, **kwargs):
        JsonPage.__init__(self, *args, **kwargs)
        if 'ads' not in self.doc:
            self.doc['ads'] = []

    @pagination
    @method
    class get_housing_list(DictElement):
        item_xpath = 'ads'

        def next_page(self):
            data = Env('data')(self)
            if data['offset'] > self.page.doc['total_all']:
                return

            data['offset'] = data['offset'] + data['limit']
            return requests.Request("POST", self.page.url, data=json.dumps(data))

        class item(ItemElement):
            klass = Housing

            def parse(self, el):
                self.env['details'] = {obj['key']: obj['value_label'] for obj in self.el['attributes']}

            obj_id = Dict('list_id')
            obj_url = Dict('url')
            obj_type = Env('query_type')

            obj_area = CleanDecimal(PopDetail('square',
                                              default=0),
                                    default=NotAvailable)
            obj_rooms = CleanDecimal(PopDetail('rooms',
                                               default=0),
                                     default=NotAvailable)

            def obj_GES(self):
                ges = CleanText(PopDetail('ges', default='|'))(self)
                return getattr(ENERGY_CLASS, ges[0], NotAvailable)

            def obj_DPE(self):
                dpe = CleanText(PopDetail('energy_rate', default='|'))(self)
                return getattr(ENERGY_CLASS, dpe[0], NotAvailable)

            def obj_house_type(self):
                value = CleanText(PopDetail('real_estate_type'), default=' ')(self).lower()
                if value == 'parking':
                    return HOUSE_TYPES.PARKING
                elif value == 'appartement':
                    return HOUSE_TYPES.APART
                elif value == 'maison':
                    return HOUSE_TYPES.HOUSE
                elif value == 'terrain':
                    return HOUSE_TYPES.LAND
                else:
                    return HOUSE_TYPES.OTHER

            def obj_utilities(self):
                value = CleanText(PopDetail('charges_included',
                                            default='Non'),
                                  default=NotAvailable)(self)
                if value == "Oui":
                    return UTILITIES.INCLUDED
                else:
                    return UTILITIES.EXCLUDED

            def obj_advert_type(self):
                line_pro = Dict('owner/type')(self)
                if line_pro == u'pro':
                    return ADVERT_TYPES.PROFESSIONAL
                else:
                    return ADVERT_TYPES.PERSONAL

            obj_title = Dict('subject')
            obj_cost = CleanDecimal(Dict('price/0'), default=Decimal(0))
            obj_currency = BaseCurrency.get_currency(u'€')
            obj_text = Dict('body')
            obj_location = Dict('location/city_label')
            obj_date = DateTime(Dict('first_publication_date'))

            def obj_photos(self):
                photos = []
                for img in Dict('images/urls_large', default=[])(self):
                    photos.append(HousingPhoto(img))
                return photos

            def obj_type(self):
                try:
                    breadcrumb = int(Dict('category_id')(self))
                except ValueError:
                    breadcrumb = None

                if breadcrumb == 11:
                    return POSTS_TYPES.SHARING
                elif breadcrumb == 10:

                    isFurnished = CleanText(PopDetail('furnished', default=' '))(self)

                    if isFurnished.lower() == u'meublé':
                        return POSTS_TYPES.FURNISHED_RENT
                    else:
                        return POSTS_TYPES.RENT
                else:
                    return POSTS_TYPES.SALE

            obj_price_per_meter = PricePerMeterFilter()
            obj_details = Env('details')


class HousingPage(HomePage):

    def get_api_key(self):
        return Dict('API/KEY_JSON')(self.api_content)

    @method
    class get_housing(ItemElement):
        klass = Housing

        def parse(self, el):
            self.env['details'] = {obj['key']: obj['value_label'] for obj in self.el['adview']['attributes']}

        obj_id = Env('_id')

        obj_area = CleanDecimal(PopDetail('square',
                                          default=0),
                                default=NotAvailable)
        obj_rooms = CleanDecimal(PopDetail('rooms',
                                           default=0),
                                 default=NotAvailable)

        def obj_GES(self):
            ges = CleanText(PopDetail('ges', default='|'))(self)
            return getattr(ENERGY_CLASS, ges[0], NotAvailable)

        def obj_DPE(self):
            dpe = CleanText(PopDetail('energy_rate', default='|'))(self)
            return getattr(ENERGY_CLASS, dpe[0], NotAvailable)

        def obj_house_type(self):
            value = CleanText(PopDetail('real_estate_type'), default=' ')(self).lower()
            if value == 'parking':
                return HOUSE_TYPES.PARKING
            elif value == 'appartement':
                return HOUSE_TYPES.APART
            elif value == 'maison':
                return HOUSE_TYPES.HOUSE
            elif value == 'terrain':
                return HOUSE_TYPES.LAND
            else:
                return HOUSE_TYPES.OTHER

        def obj_utilities(self):
            value = CleanText(PopDetail('charges_included',
                                        default='Non'),
                              default=NotAvailable)(self)
            if value == "Oui":
                return UTILITIES.INCLUDED
            else:
                return UTILITIES.EXCLUDED

        obj_title = Dict('adview/subject')
        obj_cost = CleanDecimal(Dict('adview/price/0'), default=Decimal(0))
        obj_currency = BaseCurrency.get_currency(u'€')
        obj_text = Dict('adview/body')
        obj_location = Dict('adview/location/city_label')

        def obj_advert_type(self):
            line_pro = Dict('adview/owner/type')(self)
            if line_pro == u'pro':
                return ADVERT_TYPES.PROFESSIONAL
            else:
                return ADVERT_TYPES.PERSONAL

        obj_date = DateTime(Dict('adview/first_publication_date'))

        def obj_photos(self):
            photos = []
            for img in Dict('adview/images/urls_large', default=[])(self):
                photos.append(HousingPhoto(img))
            return photos

        def obj_type(self):
            try:
                breadcrumb = int(Dict('adview/category_id')(self))
            except ValueError:
                breadcrumb = None

            if breadcrumb == 11:
                return POSTS_TYPES.SHARING
            elif breadcrumb == 10:

                isFurnished = CleanText(PopDetail('furnished', default=' '))(self)

                if isFurnished.lower() == u'meublé':
                    return POSTS_TYPES.FURNISHED_RENT
                else:
                    return POSTS_TYPES.RENT
            else:
                return POSTS_TYPES.SALE

        obj_price_per_meter = PricePerMeterFilter()
        obj_url = Dict('adview/url')
        obj_details = Env('details')


class PhonePage(JsonPage):
    def get_phone(self):
        if Dict('utils/status')(self.doc) == u'OK':
            return Dict('utils/phonenumber')(self.doc)
        return NotAvailable

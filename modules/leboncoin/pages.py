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

from weboob.browser.pages import HTMLPage, pagination, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.base import Currency as BaseCurrency
from weboob.browser.filters.standard import (CleanText, Regexp, Currency,
                                             CleanDecimal, Env, DateTime,
                                             Format, Join)
from weboob.browser.filters.html import Attr, Link, XPath
from weboob.browser.filters.json import Dict
from weboob.capabilities.housing import (City, Housing, HousingPhoto,
                                         UTILITIES, ENERGY_CLASS, POSTS_TYPES,
                                         ADVERT_TYPES, HOUSE_TYPES)
from weboob.capabilities.base import NotAvailable, empty
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.tools.date import DATE_TRANSLATE_FR, LinearDateGuesser

from decimal import Decimal
from datetime import date, timedelta
from lxml import etree
import json


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


class HousingListPage(HTMLPage):

    ENCODING = 'iso-8859-1'

    def get_area_min(self, asked_area):
        return self.find_select_value(asked_area, '//select[@id="sqs"]/option')

    def get_area_max(self, asked_area):
        return self.find_select_value(asked_area, '//select[@id="sqe"]/option')

    def get_rooms_min(self, asked_rooms):
        return self.find_select_value(asked_rooms, '//select[@id="rooms_ros"]/option')

    # def get_rooms_max(self, asked_rooms):
    #     return self.find_select_value(asked_rooms, '//select[@id="roe"]/option')

    def get_cost_min(self, asked_cost, _type):
        _id = "ps" if _type == POSTS_TYPES.SALE else "mrs"
        return self.find_select_value(asked_cost, '//select[@id="%s"]/option' % _id)

    def get_cost_max(self, asked_cost, _type):
        _id = "pe" if _type == POSTS_TYPES.SALE else "mre"
        return self.find_select_value(asked_cost, '//select[@id="%s"]/option' % _id)

    def find_select_value(self, ref_value, selector):
        select = {}
        for item in self.doc.xpath(selector):
            if item.attrib['value']:
                select[CleanDecimal('.')(item)] = CleanDecimal('./@value')(item)

        select_keys = sorted(select.keys())
        for select_value in select_keys:
            if select_value >= ref_value:
                return select[select_value]

        return select[select_keys[-1]] if select else 0

    @pagination
    @method
    class get_housing_list(ListElement):
        item_xpath = '//a[has-class("list_item")]'

        next_page = Format(u'http:%s', Link('//a[@id="next"]'))

        class item(ItemElement):
            klass = Housing

            def validate(self, obj):
                return obj.id is not None

            obj_url = Format(u'http:%s', Link('.'))
            obj_id = Regexp(Link('.'),
                            '//www.leboncoin.fr/(ventes_immobilieres|locations|colocations)/(.*).htm.*',
                            '\\2', default=None)
            obj_type = Env('query_type')

            def obj_advert_type(self):
                ispro = XPath('.//span[has-class("ispro")]', default=None)(self)
                if ispro:
                    return ADVERT_TYPES.PROFESSIONAL
                else:
                    return ADVERT_TYPES.PERSONAL

            obj_house_type = NotAvailable

            obj_title = CleanText('./@title|./section/p[@class="item_title"]')
            obj_cost = CleanDecimal('./section[@class="item_infos"]/*[@class="item_price"]/text()',
                                    replace_dots=(',', '.'),
                                    default=NotAvailable)
            obj_price_per_meter = PricePerMeterFilter()
            obj_area = CleanDecimal(
                Regexp(
                    obj_title,
                    r'(.*?)([\d,\.]*) m²(.*?)',
                    '\\2',
                    default=None
                ),
                replace_dots=True,
                default=NotAvailable
            )
            obj_location = CleanText(
                './section[@class="item_infos"]/*[@itemtype="http://schema.org/Place"]/text()'
            )
            obj_currency = Currency(
                './section[@class="item_infos"]/*[@class="item_price"]'
            )

            def obj_utilities(self):
                utilities = Regexp(CleanText('./section[@class="item_infos"]/*[@class="item_price"]'),
                                   '\d+ [%s%s%s](.*)' % (u'€', u'$', u'£'),
                                   default=u'')(self)
                if "C.C." in utilities:
                    return UTILITIES.INCLUDED
                elif "H.C." in utilities:
                    return UTILITIES.EXCLUDED
                else:
                    return UTILITIES.UNKNOWN

            obj_text = Join(' - ', './/p[@class="item_supp"]')

            def obj_date(self):
                _date = CleanText('./section[@class="item_infos"]/aside/p[@class="item_supp"]/text()',
                                  replace=[('Aujourd\'hui', str(date.today())),
                                           ('Hier', str((date.today() - timedelta(1))))])(self)

                if not _date:
                    return NotAvailable

                for fr, en in DATE_TRANSLATE_FR:
                    _date = fr.sub(en, _date)

                self.env['tmp'] = _date
                return DateTime(Env('tmp'), LinearDateGuesser())(self)

            def obj_photos(self):
                photos = []
                url = Attr(
                    './div[@class="item_image"]/span/span[@class="lazyload"]',
                    'data-imgsrc',
                    default=None
                )(self)
                if url:
                    photos.append(
                        HousingPhoto(
                            url.replace("ad-thumb", "ad-image")
                        )
                    )
                return photos


class HousingPage(HTMLPage):

    def __init__(self, *args, **kwargs):
        HTMLPage.__init__(self, *args, **kwargs)

        add_content = CleanText('(//body/script)[3]', replace=[('window.FLUX_STATE = ', '')])(self.doc)

        api_content = CleanText('(//body/script)[2]', replace=[('window.APP_CONFIG = ', '')])(self.doc)

        self.api_content = json.loads(api_content)
        self.doc = json.loads(add_content)

    @method
    class get_housing(ItemElement):
        klass = Housing

        def parse(self, el):
            details = dict()
            self.env['area'] = NotAvailable
            self.env['GES'] = NotAvailable
            self.env['DPE'] = NotAvailable
            self.env['typeBien'] = NotAvailable
            self.env['utilities'] = UTILITIES.UNKNOWN
            self.env['rooms'] = NotAvailable

            for item in Dict('adview/attributes')(self):
                key = item['key']
                value = item['value_label']

                if key == u'real_estate_type':
                    value = value.lower()
                    if value == 'parking':
                        self.env['typeBien'] = HOUSE_TYPES.PARKING
                    elif value == 'appartement':
                        self.env['typeBien'] = HOUSE_TYPES.APART
                    elif value == 'maison':
                        self.env['typeBien'] = HOUSE_TYPES.HOUSE
                    elif value == 'terrain':
                        self.env['typeBien'] = HOUSE_TYPES.LAND
                    else:
                        self.env['typeBien'] = HOUSE_TYPES.OTHER
                elif key == u'rooms':
                    self.env['rooms'] = value
                elif key == u'square':
                    self.env['area'] = Decimal(item['value'])
                elif key == u'ges':
                    self.env['GES'] = value
                elif key == u'energy_rate':
                    self.env['DPE'] = getattr(ENERGY_CLASS, item['value'].upper() ,NotAvailable)
                elif key == u'furnished':
                    self.env['isFurnished'] = (value.lower() == u'meublé')
                elif key == u'charges_included':
                    if value == "Oui":
                        self.env['utilities'] = UTILITIES.INCLUDED
                    else:
                        self.env['utilities'] = UTILITIES.EXCLUDED
                elif 'key_label' in item:
                        details[item['key_label']] = value

            self.env['details'] = details

        obj_id = Env('_id')
        obj_area = Env('area')
        obj_details = Env('details')
        obj_GES = Env('GES')
        obj_DPE = Env('DPE')

        def obj_rooms(self):
            if not empty(self.env['rooms']):
                return CleanDecimal(Env('rooms'))(self)
            else:
                return NotAvailable

        obj_house_type = Env('typeBien')
        obj_utilities = Env('utilities')
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

        obj_price_per_meter = PricePerMeterFilter()
        obj_url = Dict('adview/url')

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
                if self.env['isFurnished']:
                    return POSTS_TYPES.FURNISHED_RENT
                else:
                    return POSTS_TYPES.RENT
            else:
                return POSTS_TYPES.SALE

    def get_api_key(self):
        return Dict('API/KEY_JSON')(self.api_content)


class PhonePage(JsonPage):
    def get_phone(self):
        if Dict('utils/status')(self.doc) == u'OK':
            return Dict('utils/phonenumber')(self.doc)
        return NotAvailable

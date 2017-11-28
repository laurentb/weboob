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

from datetime import datetime

from weboob.browser.pages import JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env, Format
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.housing import (Housing, HousingPhoto, City,
                                         UTILITIES, ADVERT_TYPES)
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.capabilities.base import NotAvailable, Currency


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


class SearchPage(HTMLPage):
    @method
    class iter_housings(ListElement):
        item_xpath = '//li[@id]'

        class item(ItemElement):
            klass = Housing

            def condition(self):
                return CleanText("./@id")(self) != "pnlInfo"

            obj_id = Regexp(CleanText('./a/@href',
                                      replace=[('/annonces-immobilieres/', ''), ('/location/', '')]),
                            '(.*).html')
            obj_type = Env('query_type')
            obj_advert_type = ADVERT_TYPES.PERSONAL
            obj_house_type = NotAvailable  # TODO

            def obj_title(self):
                title = CleanText('./a/div/p/span[@class="item title"]')(self)
                if title == "":
                    title = CleanText('./a/div/p/span[@class="item loc"]')(self)
                return title

            obj_cost = CleanDecimal(CleanText('./a/div/p/span[@class="item prix"]', children=False))
            obj_currency = Currency(u'€')
            obj_text = Format('%s / %s / %s / %s',
                              CleanText('./a/div/p/span[@class="item type"]/img/@alt'),
                              CleanText('./a/div/p/span[@id="divnbpieces"]', children=False),
                              CleanText('./a/div/p/span[@id="divsurface"]', children=False),
                              CleanText('./a/div/p/span[@class="item prix"]/span'))
            obj_utilities = UTILITIES.UNKNOWN


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_type = NotAvailable  # TODO
        obj_advert_type = ADVERT_TYPES.PERSONAL
        obj_house_type = NotAvailable  # TODO
        obj_title = CleanText('h1')

        obj_rooms = CleanDecimal('//div[@class="stats"]/section/div[@id="divpieces"]/span[@class="stat"]', default=0)

        obj_currency = u'EUR'
        obj_cost = CleanDecimal('(//div[@class="stats"]/div/h2)[2]/em')
        obj_utilities = UTILITIES.UNKNOWN
        obj_text = CleanHTML('//div[@class="textes"]')
        obj_location = CleanText('//input[@id="adressegeo"]/@value')
        obj_url = CleanText('//input[@id="hfurldetail"]/@value')

        obj_area = CleanDecimal(Regexp(
                    CleanText('//div[@class="stats"]/section/div[@id="divsurface"]/span[@class="stat"]'),
                    u'\s?(\d+)\sm\s2',
                    default=NotAvailable
                ),
                default=NotAvailable
            )

        obj_price_per_meter = PricePerMeterFilter()
        obj_phone = CleanText('//input[@id="hftelA"]/@value')
        obj_date = datetime.now

        def obj_photos(self):
            photos = []
            for photo in self.xpath('//div[@id="plistimage"]/a/@urlbig'):
                photos.append(HousingPhoto(u"http://www.entreparticuliers.com/%s" % photo))
            return photos

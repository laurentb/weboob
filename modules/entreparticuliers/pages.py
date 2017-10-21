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
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env
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


class SearchPage(HTMLPage):
    @method
    class iter_housings(ListElement):
        item_xpath = '//li[@id="0"]'

        class item(ItemElement):
            klass = Housing

            obj_id = Regexp(CleanText('./a/@href'), '/annonces-immobilieres/(.*).html')
            obj_title = CleanText('./a/div/p/span[@class="item title"]')
            obj_cost = CleanDecimal('./a/div/p/span[@class="item prix"]')
            obj_currency = u'€'
            obj_text = CleanText('./a/div[@class="txt-xs"]')
            obj_utilities = UTILITIES.UNKNOWN


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('h1')

        obj_rooms = CleanDecimal('//div[@class="stats"]/section/div[@id="divpieces"]/span[@class="stat"]')

        obj_cost = CleanDecimal('(//div[@class="stats"]/div/h2)[2]')
        obj_currency = u'€'
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

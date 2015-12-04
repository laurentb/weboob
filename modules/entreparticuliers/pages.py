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

from weboob.browser.pages import JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env, BrowserURL
from weboob.capabilities.housing import Housing, HousingPhoto, City
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
        item_xpath = '//ul[@class="results rview"]/li'

        class item(ItemElement):
            klass = Housing

            def condition(self):
                return CleanText('./div/span[@class="infos"]/a[@class="titre"]/@href')(self)

            obj_id = Regexp(CleanText('./div/span[@class="infos"]/a[@class="titre"]/@href'),
                            '/(.*).html')
            obj_title = CleanText('./div/span[@class="infos"]/a[@class="titre"]')
            obj_cost = CleanDecimal(Regexp(CleanText('./div/span[@class="infos"]/span[@id="prix"]'),
                                           '(.*) [%s%s%s].*' % (u'€', u'$', u'£'),
                                           default=''),
                                    replace_dots=(',', '.'),
                                    default=Decimal(0))
            obj_currency = Regexp(CleanText('./div/span[@class="infos"]/span[@id="prix"]'),
                                  '.*([%s%s%s]).*' % (u'€', u'$', u'£'), default=u'€')
            obj_text = CleanText('./div/span[@class="infos"]')
            obj_date = datetime.now


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//main/section/div/h1')
        obj_cost = CleanDecimal('//span[@class="i prix"]', replace_dots=(',', '.'), default=Decimal(0))

        obj_currency = Regexp(CleanText('//span[@class="i prix"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default='')
        obj_text = CleanHTML('//article[@class="bloc description"]/p')
        obj_location = CleanText('//span[@class="i ville"]')
        obj_area = CleanDecimal(Regexp(CleanText('//span[@class="i"]'), '.*/(.*) m.*', default=NotAvailable),
                                default=NotAvailable)
        obj_url = BrowserURL('housing', _id=Env('_id'))
        obj_phone = CleanText('//input[@id="hftel"]/@value')
        obj_date = datetime.now

        def obj_details(self):
            details = {}
            for detail in self.el.xpath('//span[@class="i small"]'):
                item = detail.text.split(':')
                details[item[0]] = item[1]
            return details

        def obj_photos(self):
            photos = []
            for img in self.el.xpath('//ul[@id="ulPhotos"]/li/img/@src'):
                url = u'http://www.entreparticuliers.com/%s' % img
                photos.append(HousingPhoto(url))
            return photos

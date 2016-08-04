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


from decimal import Decimal

from weboob.tools.date import parse_french_date
from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env, BrowserURL, Format
from weboob.browser.filters.html import Link, XPath, CleanHTML
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing, City, HousingPhoto
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter


class CitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):

        class item(ItemElement):
            klass = City

            obj_id = Dict('id')
            obj_name = Dict('name')


class SearchResultsPage(HTMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = '//div[has-class("annonce")]'

        def next_page(self):
            return Link('//ul[@class="pagination"]/li[@class="next"]/a')(self)

        class item(ItemElement):
            klass = Housing

            def condition(self):
                return Regexp(Link('./div[@class="box-header"]/a'), '/annonces/(.*)', default=None)(self)

            obj_id = Regexp(Link('./div[@class="box-header"]/a'), '/annonces/(.*)')
            obj_title = CleanText('./div[@class="box-header"]/a[@class="title-item"]')
            obj_area = CleanDecimal(Regexp(CleanText('./div[@class="box-header"]/a/span[@class="h1"]'),
                                           '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
            obj_cost = CleanDecimal(CleanText('./div[@class="box-header"]/a/span[@class="price"]'),
                                    replace_dots=True, default=Decimal(0))
            obj_currency = Regexp(CleanText('./div[@class="box-header"]/a/span[@class="price"]'),
                                  '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')

            def obj_date(self):
                _date = Regexp(CleanText('./div[@class="box-header"]/p[@class="date"]'),
                               '.* / (.*)')(self)
                return parse_french_date(_date)

            obj_station = CleanText('./div/div/div[@cladd=metro]', default=NotAvailable)
            obj_location = CleanText('./div[@class="box-body"]/div/div/p[@class="item-description"]/strong')
            obj_text = CleanText('./div[@class="box-body"]/div/div/p[@class="item-description"]')

            def obj_photos(self):
                photos = []
                for img in XPath('./div[@class="box-body"]/div/div/a/img/@src')(self):
                    photos.append(HousingPhoto(u'%s' % img))
                return photos


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//h1[@class="clearfix"]/span[@class="title"]')
        obj_cost = CleanDecimal('//h1[@class="clearfix"]/span[@class="price"]',
                                replace_dots=True)
        obj_currency = Regexp(CleanText('//h1[@class="clearfix"]/span[@class="price"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
        obj_area = CleanDecimal(Regexp(CleanText('//h1[@class="clearfix"]/span[@class="title"]'),
                                '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
        obj_price_per_meter = PricePerMeterFilter()
        obj_location = CleanText('//div[@class="item-geoloc"]/h2')
        obj_text = CleanText(CleanHTML('//p[@class="item-description"]'))
        obj_station = CleanText('//div[@class="metro"]')
        obj_phone = CleanHTML('(//div[has-class("tel-wrapper")])[1]')
        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_details(self):
            details = dict()
            for item in XPath('//ul[@class="item-summary"]/li')(self):
                key = CleanText('.', children=False)(item)
                value = CleanText('./strong')(item)
                if value and key:
                    details[key] = value

            key = CleanText('//div[@class="box energy-box"]/div/div/p[@class="h3"]')(self)
            value = Format('%s(%s)', CleanText('(//div[@class="box energy-box"]/div/div/p)[2]'),
                           CleanText('//div[@class="box energy-box"]/div/div/@class',
                                     replace=[('-', ''), ('rank', '')]))(self)
            if value and key:
                details[key] = value
            return details

        def obj_photos(self):
            photos = []
            for img in XPath('//div[has-class("showcase-thumbnail")]/img/@src')(self):
                photos.append(HousingPhoto(u'%s' % img))
            return photos

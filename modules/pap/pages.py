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
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env, BrowserURL, Format
from weboob.browser.filters.html import Link, XPath, CleanHTML
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing, City, HousingPhoto


class DictElement(ListElement):
    def find_elements(self):
        if self.item_xpath is not None:
            for el in self.el:
                yield el
        else:
            yield self.el


class CitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        item_xpath = '.'

        class item(ItemElement):
            klass = City

            obj_id = Dict('id')
            obj_name = Dict('name')


class SearchResultsPage(HTMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = '//li[@class="annonce"]'

        def next_page(self):
            return Link('//ul[@class="pagination"]/li[@class="next"]/a')(self)

        class item(ItemElement):
            klass = Housing

            def condition(self):
                return Regexp(Link('./div[@class="header-annonce"]/a'), '/annonces/(.*)', default=None)(self)

            obj_id = Regexp(Link('./div[@class="header-annonce"]/a'), '/annonces/(.*)')
            obj_title = CleanText('./div[@class="header-annonce"]/a')
            obj_area = CleanDecimal(Regexp(CleanText('./div[@class="header-annonce"]/a/span[@class="desc"]'),
                                           '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
            obj_cost = CleanDecimal(CleanText('./div[@class="header-annonce"]/a/span[@class="prix"]'),
                                    replace_dots=(',', '.'), default=Decimal(0))
            obj_currency = Regexp(CleanText('./div[@class="header-annonce"]/a/span[@class="prix"]'),
                                  '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')

            def obj_date(self):
                _date = CleanText('./div[@class="header-annonce"]/span[@class="date"]')(self)
                return parse_french_date(_date)

            obj_station = CleanText('./div/div/div[@cladd=metro]', default=NotAvailable)
            obj_location = CleanText('./div[@class="clearfix"]/div/a/span/img/@alt')
            obj_text = CleanText('./div[@class="clearfix"]/div[@class="description clearfix"]/p')

            def obj_photos(self):
                photos = []
                for img in XPath('//div[@class="vignette-annonce"]/a/span/img/@src')(self):
                    photos.append(HousingPhoto(u'%s' % img))
                return photos


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//h1[@class="desc clearfix"]/span[@class="title"]')
        obj_cost = CleanDecimal('//h1[@class="desc clearfix"]/span[@class="prix"]')
        obj_currency = Regexp(CleanText('//h1[@class="desc clearfix"]/span[@class="prix"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
        obj_area = CleanDecimal(Regexp(CleanText('//h1[@class="desc clearfix"]/span[@class="title"]'),
                                '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
        obj_location = CleanText('//div[@class="text-annonce"]/h2')
        obj_text = CleanHTML('//div[@class="text-annonce"]/p')
        obj_station = CleanText('//div[@class="metro"]')
        obj_phone = CleanText('//span[@class="telephone hide-tel"]')
        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_details(self):
            details = dict()
            for item in XPath('//div[@class="footer-descriptif"]/ul/li')(self):
                key = CleanText('./span[@class="label"]')(item)
                value = CleanText('.', replace=[(key, '')])(item)
                if value and key:
                    details[key] = value

            key = CleanText('//div[@class="classe-energie-content"]/div/div/span')(self)
            value = Format('%s(%s)', CleanText('//div[@class="classe-energie-content"]/div/div/p'),
                           CleanText('//div[@class="classe-energie-content"]/div/@class',
                                     replace=[('-', ' ')]))(self)
            if value and key:
                details[key] = value
            return details

        def obj_photos(self):
            photos = []
            for img in XPath('//div[@class="showcase-thumbnail"]/img/@src')(self):
                photos.append(HousingPhoto(u'%s' % img))
            return photos

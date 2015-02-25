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

import re
from decimal import Decimal
from datetime import datetime
from weboob.browser.filters.json import Dict
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import JsonPage, HTMLPage, pagination
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env, BrowserURL, Filter, Format
from weboob.browser.filters.html import CleanHTML, XPath
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.capabilities.housing import Housing, HousingPhoto, City


class DictElement(ListElement):
    def find_elements(self):
        for el in self.el[0].get(self.item_xpath):
            yield el


class CitiesPage(JsonPage):
    @method
    class get_cities(DictElement):
        item_xpath = 'locations'

        class item(ItemElement):
            klass = City

            obj_id = Dict('label')
            obj_name = Dict('label')


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = '//div[starts-with(@id, "bloc-vue-")]'

        def next_page(self):
            js_datas = CleanText('//div[@id="js-data"]/@data-rest-search-request')(self)
            total_page = self.page.browser.get_total_page(js_datas.split('?')[-1])
            m = re.match(".*page=(\d?)(?:&.*)?", self.page.url)
            if m:
                current_page = int(m.group(1))
                next_page = current_page + 1
                if next_page <= total_page:
                    return self.page.url.replace('page=%d' % current_page, 'page=%d' % next_page)

        class item(ItemElement):
            klass = Housing

            obj_id = CleanText('./@data-classified-id')
            obj_title = CleanText('./div/h2[@itemprop="name"]/a')
            obj_location = CleanText('./div/h2[@itemprop="name"]/span[class="item-localisation"]')
            obj_cost = CleanDecimal('./div/div/span[@class="price-label"]')
            obj_currency = Regexp(CleanText('./div/div/span[@class="price-label"]'),
                                  '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
            obj_text = CleanText('./div/div/div[@itemprop="description"]')
            obj_area = CleanDecimal(Regexp(CleanText('./div/h2[@itemprop="name"]/a'),
                                           '(.*?)(\d*) m2(.*?)', '\\2', default=None),
                                    default=NotAvailable)

            def obj_phone(self):
                phone = CleanText('./div/div/ul/li/span[@class="js-clickphone"]',
                                  replace=[(u'Téléphoner : ', u'')],
                                  default=NotAvailable)(self)

                if '...' in phone:
                    return NotLoaded
                return phone

            def obj_photos(self):
                url = CleanText('./div/div/a/img[@itemprop="image"]/@src')(self)
                return [HousingPhoto(url)]


class TypeDecimal(Filter):
    def filter(self, el):
        return Decimal(el)


class FromTimestamp(Filter):
    def filter(self, el):
        return datetime.fromtimestamp(el / 1000.0)


class PhonePage(JsonPage):
    def get_phone(self):
        return self.doc.get('phoneNumber')


class HousingPage2(JsonPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = Dict('characteristics/titleWithTransaction')
        obj_location = Format('%s %s %s', Dict('location/address'),
                              Dict('location/postalCode'), Dict('location/cityLabel'))
        obj_cost = TypeDecimal(Dict('characteristics/price'))
        obj_currency = u'€'
        obj_text = CleanHTML(Dict('characteristics/description'))
        obj_url = BrowserURL('housing_html', _id=Env('_id'))
        obj_area = TypeDecimal(Dict('characteristics/area'))
        obj_date = FromTimestamp(Dict('characteristics/date'))

        def obj_photos(self):
            photos = []
            for img in Dict('characteristics/images')(self):
                m = re.search('http://thbr\.figarocms\.net.*(http://.*)', img)
                if m:
                    photos.append(HousingPhoto(m.group(1)))
                else:
                    photos.append(HousingPhoto(img))
            return photos

        def obj_details(self):
            details = {}
            details['fees'] = Dict('characteristics/fees')(self)
            details['bedrooms'] = Dict('characteristics/bedroomCount')(self)
            details['energy'] = Dict('characteristics/energyConsumptionCategory')(self)
            rooms = Dict('characteristics/roomCount')(self)
            if len(rooms):
                details['rooms'] = rooms[0]
            details['available'] = Dict('characteristics/available')(self)
            return details

    def get_total_page(self):
        return self.doc.get('pagination').get('total')


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//h1[@itemprop="name"]')
        obj_location = CleanText('//span[@class="informations-localisation"]')
        obj_cost = CleanDecimal('//span[@itemprop="price"]')
        obj_currency = Regexp(CleanText('//span[@itemprop="price"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
        obj_text = CleanHTML('//div[@itemprop="description"]')
        obj_url = BrowserURL('housing', _id=Env('_id'))
        obj_area = CleanDecimal(Regexp(CleanText('//h1[@itemprop="name"]'),
                                       '(.*?)(\d*) m2(.*?)', '\\2'), default=NotAvailable)

        def obj_photos(self):
            photos = []
            for img in XPath('//a[@class="thumbnail-link"]/img[@itemprop="image"]')(self):
                url = Regexp(CleanText('./@src'), 'http://thbr\.figarocms\.net.*(http://.*)')(img)
                photos.append(HousingPhoto(url))
            return photos

        def obj_details(self):
            details = dict()
            for item in XPath('//div[@class="features clearfix"]/ul/li')(self):
                key = CleanText('./span[@class="name"]')(item)
                value = CleanText('./span[@class="value"]')(item)
                if value and key:
                    details[key] = value

            key = CleanText('//div[@class="title-dpe clearfix"]')(self)
            value = CleanText('//div[@class="energy-consumption"]')(self)
            if value and key:
                details[key] = value
            return details

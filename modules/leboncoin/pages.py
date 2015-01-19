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
from decimal import Decimal
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, Env, DateTime, BrowserURL, Format
from weboob.browser.filters.html import Attr, Link, CleanHTML
from weboob.capabilities.housing import City, Housing, HousingPhoto
from weboob.capabilities.base import NotAvailable
from datetime import date, timedelta
from weboob.tools.date import DATE_TRANSLATE_FR, LinearDateGuesser


class CityListPage(HTMLPage):
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
    def get_area_min(self, asked_area):
        return self.find_select_value(asked_area, '//select[@id="sqs"]/option')

    def get_area_max(self, asked_area):
        return self.find_select_value(asked_area, '//select[@id="sqe"]/option')

    def get_rooms_min(self, asked_rooms):
        return self.find_select_value(asked_rooms, '//select[@id="rooms_ros"]/option')

    # def get_rooms_max(self, asked_rooms):
    #     return self.find_select_value(asked_rooms, '//select[@id="roe"]/option')

    def get_cost_min(self, asked_cost):
        return self.find_select_value(asked_cost, '//select[@id="ps"]/option')

    def get_cost_max(self, asked_cost):
        return self.find_select_value(asked_cost, '//select[@id="pe"]/option')

    def find_select_value(self, ref_value, selector):
        select = {}
        for item in self.doc.xpath(selector):
            if item.attrib['value']:
                select[CleanDecimal('.')(item)] = CleanDecimal('./@value')(item)

        select_keys = select.keys()
        select_keys.sort()
        for select_value in select_keys:
            if select_value >= ref_value:
                return select[select_value]

        return select[select_keys[-1]]

    @pagination
    @method
    class get_housing_list(ListElement):
        item_xpath = '//div[@class="list-lbc"]/a'

        def next_page(self):
            return Link('//li[@class="page"]/a[contains(text(),"Page suivante")]')(self)

        class item(ItemElement):
            klass = Housing

            obj_id = Regexp(Link('.'), 'http://www.leboncoin.fr/(ventes_immobilieres|locations)/(.*).htm', '\\2')
            obj_title = CleanText('./div[@class="lbc"]/div/div[@class="title"]')
            obj_cost = CleanDecimal('./div[@class="lbc"]/div/div[@class="price"]',
                                    replace_dots=(',', '.'),
                                    default=Decimal(0))
            obj_currency = Regexp(CleanText('./div[@class="lbc"]/div/div[@class="price"]'),
                                  '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
            obj_text = CleanText('./div[@class="lbc"]/div[@class="detail"]')

            def obj_date(self):
                _date = CleanText('./div[@class="lbc"]/div[@class="date"]',
                                  replace=[('Aujourd\'hui', str(date.today())),
                                           ('Hier', str((date.today() - timedelta(1))))])(self)
                for fr, en in DATE_TRANSLATE_FR:
                    _date = fr.sub(en, _date)

                self.env['tmp'] = _date
                return DateTime(Env('tmp'), LinearDateGuesser())(self)

            def obj_photos(self):
                photos = []
                url = Attr('./div[@class="lbc"]/div[@class="image"]/div/img', 'src', default=None)(self)
                if url:
                    photos.append(HousingPhoto(url))
                return photos


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        def parse(self, el):
            details = dict()
            self.env['location'] = NotAvailable
            for tr in el.xpath('//div[@class="floatLeft"]/table/tr'):
                if 'Ville' in CleanText('./th')(tr):
                    self.env['location'] = CleanText('./td')(tr)
                else:
                    details['%s' % CleanText('./th', replace=[(':', '')])(tr)] = CleanText('./td')(tr)

            self.env['area'] = NotAvailable
            for tr in el.xpath('//div[@class="lbcParams criterias"]/table/tr'):
                if 'Surface' in CleanText('./th')(tr):
                    self.env['area'] = CleanDecimal(Regexp(CleanText('./td'), '(.*)m.*'),
                                                    replace_dots=(',', '.'))(tr)
                else:
                    key = '%s' % CleanText('./th', replace=[(':', '')])(tr)
                    if 'GES' in key or 'Classe' in key:
                        details[key] = CleanText('./td/noscript/a')(tr)
                    else:
                        details[key] = CleanText('./td')(tr)

            self.env['details'] = details

        obj_id = Env('_id')
        obj_title = CleanText('//h2[@id="ad_subject"]')
        obj_cost = CleanDecimal('//span[@class="price"]', replace_dots=(',', '.'), default=Decimal(0))

        obj_currency = Regexp(CleanText('//span[@class="price"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default='')
        obj_text = CleanHTML('//div[@class="content"]')
        obj_location = Env('location')
        obj_details = Env('details')
        obj_area = Env('area')
        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_date(self):
            _date = Regexp(CleanText('//div[@class="upload_by"]', replace=[(u'à', '')]),
                           '.*- Mise en ligne le (.*).')(self)

            for fr, en in DATE_TRANSLATE_FR:
                _date = fr.sub(en, _date)

            self.env['tmp'] = _date
            return DateTime(Env('tmp'), LinearDateGuesser())(self)

        def obj_photos(self):
            photos = []
            for img in self.el.xpath('//div[@id="thumbs_carousel"]/a/span'):
                url = CleanText(Regexp(Attr('.', 'style',
                                            default=''),
                                       "background-image: url\('(.*)'\);",
                                       default=''),
                                replace=[('thumbs', 'images')],
                                default='')(img)
                if url:
                    photos.append(HousingPhoto(url))
            return photos

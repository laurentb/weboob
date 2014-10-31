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

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Format, CleanText, Regexp, CleanDecimal, Date, Env, BrowserURL
from weboob.browser.filters.html import XPath
from weboob.capabilities.housing import Housing, HousingPhoto, City
from weboob.capabilities.base import NotAvailable


class DictElement(ListElement):
    def find_elements(self):
        for el in self.el:
            yield el


class CitiesPage(JsonPage):
    @method
    class get_cities(DictElement):
        item_xpath = ''

        class item(ItemElement):
            klass = City

            obj_id = Format('%s_%s', Dict('lct_id'), Dict('lct_level'))
            obj_name = Format('%s %s', Dict('lct_name'), Dict('lct_post_code'))


class PhonePage(HTMLPage):
    def get_phone(self):
        return CleanText('//div[has-class("phone")]', childs=False)(self.doc)


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//meta[@itemprop="name"]/@content')
        obj_area = CleanDecimal(Regexp(CleanText('//meta[@itemprop="name"]/@content'),
                                       '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
        obj_cost = CleanDecimal('//span[@itemprop="price"]')
        obj_currency = Regexp(CleanText('//span[@itemprop="price"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
        obj_date = Date(Regexp(CleanText('//p[@class="size_11 darkergrey"]'), u'.* Mis à jour : (\d{2}/\d{2}/\d{4}).*'))
        obj_text = CleanText('//div[@class="columns offer-description alpha"]')
        obj_location = CleanText('//span[@itemprop="address"]')
        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_photos(self):
            photos = []
            for img in XPath('//div[@class="carousel"]/ul/li/a/img/@src')(self):
                photos.append(HousingPhoto(u'%s' % img))
            return photos

        def obj_details(self):
            details = {}
            a = CleanText('//div[@class="box box-noborder"]/p[@class="size_13 darkergrey bold"]')(self)
            if a:
                splitted_a = a.split(':')
                dpe = Regexp(CleanText('//div[@id="energy-pyramid"]/img/@src'),
                             'http://mmf.logic-immo.com/mmf/fr/static/dpe/dpe_(\w)_b.gif',
                             default="")(self)
                if len(splitted_a) > 1:
                    details[splitted_a[0]] = '%s (%s)' % (splitted_a[1], dpe)
                elif dpe:
                    details[splitted_a[0]] = '%s'
            return details

    def get_phone_url_datas(self):
        a = XPath('//a[has-class("phone-link")]')(self.doc)[0]
        urlcontact = CleanText('./@data-urlcontact')(a)
        params = {}
        params['univers'] = CleanText('./@data-univers')(a)
        params['pushcontact'] = CleanText('./@data-pushcontact')(a)
        params['mapper'] = CleanText('./@data-mapper')(a)
        params['offerid'] = CleanText('./@data-offerid')(a)
        params['offerflag'] = CleanText('./@data-offerflag')(a)
        params['campaign'] = CleanText('./@data-campaign')(a)
        params['xtpage'] = CleanText('./@data-xtpage')(a)
        return urlcontact, params


class SearchPage(HTMLPage):
    @method
    class iter_housings(ListElement):
        item_xpath = '//article'

        class item(ItemElement):
            klass = Housing

            obj_id = Format('%s-%s', Env('type'), CleanText('./div/header/@id', replace=[('header-offer-', '')]))
            obj_title = CleanText('./div/header/section/p[@class="property-type"]/span/@title')
            obj_area = CleanDecimal(Regexp(CleanText('./div/header/section/p[@class="property-type"]/span/@title'),
                                           '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
            obj_cost = CleanDecimal(CleanText('./div/header/section/p[@class="price"]'),
                                    replace_dots=(',', '.'), default=Decimal(0))
            obj_currency = Regexp(CleanText('./div/header/section/p[@class="price"]'),
                                  '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
            obj_date = Date(Regexp(CleanText('./div/header/section/p[has-class("update-date")]'),
                                   ".*(\d{2}/\d{2}/\d{4}).*"))
            obj_text = CleanText('./div/div[@class="content-offer"]/section[has-class("content-desc")]/p/span[@intemprop="adress"]')
            obj_location = CleanText('./div/div[@class="content-offer"]/section[has-class("content-desc")]/p/span[not(@intemprop)]')

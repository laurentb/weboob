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
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Format, CleanText, Regexp, CleanDecimal, Date, Env, BrowserURL
from weboob.browser.filters.html import XPath, CleanHTML
from weboob.capabilities.housing import Housing, HousingPhoto, City
from weboob.capabilities.base import NotAvailable


class CitiesPage(JsonPage):
    @method
    class get_cities(DictElement):
        class item(ItemElement):
            klass = City

            obj_id = Format('%s_%s', Dict('lct_id'), Dict('lct_level'))
            obj_name = Format('%s %s', Dict('lct_name'), Dict('lct_post_code'))


class PhonePage(HTMLPage):
    def get_phone(self):
        return CleanText('//div[has-class("phone")]', children=False)(self.doc)


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//meta[@itemprop="name"]/@content')
        obj_area = CleanDecimal(Regexp(CleanText('//meta[@itemprop="name"]/@content'),
                                       '(.*?)(\d*) m\xb2(.*?)', '\\2'), default=NotAvailable)
        obj_cost = CleanDecimal('//div[@itemprop="price"]')
        obj_currency = Regexp(CleanText('//div[@itemprop="price"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
        obj_date = Date(Regexp(CleanText('//p[@class="offer-description-notes"]'),
                               u'.* Mis à jour : (\d{2}/\d{2}/\d{4}).*'))
        obj_text = CleanHTML('//div[@class="offer-description-text"]')
        obj_location = CleanText('//div[@itemprop="address"]')
        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_photos(self):
            photos = []
            for img in XPath('//div[@class="carousel-content"]/ul/li/a/img/@src')(self):
                photos.append(HousingPhoto(u'%s' % img))
            return photos

        def obj_details(self):
            details = {}
            energy = CleanText('//div[has-class("energy-summary")]/span[@class="section-label"]', default='')(self)
            energy_value = CleanText('//div[has-class("energy-summary")]/div[@class="arrow "]', default='')(self)
            if energy and energy_value:
                details[energy] = energy_value

            greenhouse = CleanText('//div[has-class("greenhouse-summary")]/span[@class="section-label"]',
                                   default='')(self)
            greenhouse_value = CleanText('//div[has-class("greenhouse-summary")]/div[@class="arrow "]',
                                         default='')(self)
            if greenhouse and greenhouse_value:
                details[greenhouse] = greenhouse_value

            for li in XPath('//ul[@itemprop="description"]/li')(self):
                label = CleanText('./div[has-class("criteria-label")]')(li)
                value = CleanText('./div[has-class("criteria-value")]')(li)
                details[label] = value

            return details

    def get_phone_url_datas(self):
        a = XPath('//button[has-class("offer-contact-vertical-phone")]')(self.doc)[0]
        urlcontact = 'http://www.logic-immo.com/modalMail'
        params = {}
        params['universe'] = CleanText('./@data-univers')(a)
        params['source'] = CleanText('./@data-source')(a)
        params['pushcontact'] = CleanText('./@data-pushcontact')(a)
        params['mapper'] = CleanText('./@data-mapper')(a)
        params['offerid'] = CleanText('./@data-offerid')(a)
        params['offerflag'] = CleanText('./@data-offerflag')(a)
        params['campaign'] = CleanText('./@data-campaign')(a)
        params['xtpage'] = CleanText('./@data-xtpage')(a)
        params['offertransactiontype'] = CleanText('./@data-offertransactiontype')(a)
        params['aeisource'] = CleanText('./@data-aeisource')(a)
        params['shownumber'] = CleanText('./@data-shownumber')(a)
        params['corail'] = 1
        return urlcontact, params


class SearchPage(HTMLPage):
    @method
    class iter_housings(ListElement):
        item_xpath = '//div[@class="offer-block "]'

        class item(ItemElement):
            klass = Housing

            obj_id = Format('%s-%s', Env('type'), CleanText('./@id', replace=[('header-offer-', '')]))
            obj_title = CleanText('./div/div/div[@class="offer-details-wrapper"]/div/div/p[@class="offer-type"]/span/@title')
            obj_area = CleanDecimal(CleanText('./div/div/div[@class="offer-details-wrapper"]/div/div/div/div/h3/a/span[@class="offer-area-number"]',
                                              default=NotAvailable))
            obj_cost = CleanDecimal(Regexp(CleanText('./div/div/div[@class="offer-details-wrapper"]/div/div/p[@class="offer-price"]/span',
                                                     default=NotAvailable),
                                           '(.*) [%s%s%s]' % (u'€', u'$', u'£'),
                                           default=NotAvailable), default=Decimal(0))
            obj_currency = Regexp(CleanText('./div/div/div[@class="offer-details-wrapper"]/div/div/p[@class="offer-price"]/span',
                                            default=NotAvailable),
                                  '.* ([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
            obj_date = Date(Regexp(CleanText('./div/div/div[has-class("offer-picture-more")]/div/p[@class="offer-update"]'),
                                   ".*(\d{2}/\d{2}/\d{4}).*"))
            obj_text = CleanText('./div/div/div[@class="offer-details-wrapper"]/div/div/div/p[has-class("offer-description")]/span')
            obj_location = CleanText('./div/div/div[@class="offer-details-wrapper"]/div/div/div/div/h2')

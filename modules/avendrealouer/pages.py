# -*- coding: utf-8 -*-

# Copyright(C) 2017      ZeHiro
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import datetime

from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method, DictElement
from weboob.browser.filters.html import Attr, AbsoluteLink, Link
from weboob.browser.filters.json import Dict

from weboob.browser.filters.standard import CleanDecimal, CleanText, Date, Regexp, Async, AsyncLoad

from weboob.capabilities.housing import City, Housing, UTILITIES, HousingPhoto
from weboob.capabilities.base import NotAvailable, Currency

from weboob.tools.capabilities.housing.housing import PricePerMeterFilter


class CitiesPage(JsonPage):

    @method
    class iter_cities(DictElement):

        class item(ItemElement):
            klass = City
            obj_id = Dict('Value')
            obj_name = Dict('Name')


class AvendreAlouerItem(ItemElement):
    klass = Housing
    _url = AbsoluteLink('.//a[has-class("linkCtnr")]')

    load_details = _url & AsyncLoad

    obj_url = _url
    obj_id = Async('details') & CleanText(Regexp(CleanText('//p[has-class("property-reference")]'), r'\:(.*)$', default=''))

    obj_title = CleanText('.//a//ul')
    obj_area = CleanDecimal(
        CleanText('.//a//ul//li[has-class("first")]//following-sibling::li[2]'),
        default=NotAvailable
    )

    obj_cost = CleanDecimal(
        CleanText('.//span[has-class("price")]')
    )
    obj_price_per_meter = PricePerMeterFilter()
    obj_currency = CleanText(
        Regexp(
            CleanText('.//span[has-class("price")]'),
            r'[\d\ ]+(.*)'
        )
    )

    obj_location = CleanText('.//span[has-class("loca")]')
    obj_text = CleanText('.//p[has-class("propShortDesc")]')

    obj_date = Async('details') & Date(
        Regexp(
            CleanText('//div[has-class("property-description-main")]'),
            r'Mise à jour le ([\d\\]+)', default=datetime.today()
        )
    )

    def obj_details(self):
        page_doc = Async('details').loaded_page(self).doc

        return {
            'GES': CleanText('//span[@id="gassymbol"]', '')(page_doc),
            'DPE': CleanText('//span[@id="energysymbol"]', '')(page_doc),
        }

    def obj_utilities(self):
        price = CleanText('//span[has-class("price-info")]')(self)
        if 'CC' in price:
            return UTILITIES.INCLUDED
        elif 'HC' in price:
            return UTILITIES.EXCLUDED
        else:
            return UTILITIES.UNKNOWN

    obj_station = 'Test'
    obj_bedrooms = Async('details') & CleanDecimal(
        CleanText('.//td//span[contains(text(), "Chambre")]//following-sibling::span[has-class("r")]'),
        default=NotAvailable
    )

    obj_rooms = Async('details') & CleanDecimal(
        CleanText('.//td//span[contains(text(), "Pièce")]//following-sibling::span[has-class("r")]'),
        default=NotAvailable
    )

    def obj_photos(self):
        page_doc = Async('details').loaded_page(self).doc
        photos = []
        for photo in page_doc.xpath('//div[@id="bxSliderContainer"]//ul//li//img'):
            url = Attr('.', 'src')(photo)
            if url[0] != '/':
                photos.append(HousingPhoto(url))
        return photos

    def validate(self, obj):
        return obj.id != ''


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = './/li[@data-tranid="1"]'

        next_page = AbsoluteLink('./ul[has-class("pagination")]/li/a[has-class("next")]')

        class item(AvendreAlouerItem):
            obj_phone = CleanText(Attr('.', 'data-infos'))

    def get_housing_url(self):
        return Link('.//a[has-class("picCtnr")]')(self.doc)


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing
        obj_id = Regexp(CleanText('//p[has-class("property-reference")]'), r'\:(.*)$')

        def obj_url(self):
            return self.page.url

        obj_area = CleanDecimal(
            Regexp(
                CleanText('//table[@id="table"]//span[contains(text(), "Surface")]//following-sibling::span[has-class("r")]'),
                r'([\d\ ]+)m'
            ),
            default=NotAvailable
        )
        obj_title = CleanText('//span[has-class("mainh1")]')
        obj_cost = CleanDecimal('//span[has-class("price-info")]')
        obj_currency = Currency.get_currency(u'€')
        obj_rooms = CleanDecimal('//table[@id="table"]//span[contains(text(), "Pièce")]//following-sibling::span[has-class("r")]')
        obj_bedrooms = CleanDecimal('//table[@id="table"]//span[contains(text(), "Chambre")]//following-sibling::span[has-class("r")]')
        obj_location = CleanText(Regexp(CleanText('//span[has-class("mainh1")]'), r',(.+)$'))
        obj_text = CleanText('//div[has-class("property-description-main")]')
        obj_date = Date(
            Regexp(
                CleanText('//div[has-class("property-description-main")]'),
                r'Mise à jour le ([\d\\]+)', default=datetime.today()
            )
        )
        obj_phone = Attr('//button[@id="display-phonenumber-1"]', 'data-phone-number')

        def obj_photos(self):
            photos = []
            for photo in self.xpath('//div[@id="bxSliderContainer"]//ul//li//img'):
                url = Attr('.', 'src')(photo)
                if url[0] != '/':
                    photos.append(HousingPhoto(url))
            return photos

        def obj_details(self):
            return {
                'GES': CleanText('//span[@id="gassymbol"]', '')(self),
                'DPE': CleanText('//span[@id="energysymbol"]', '')(self),
            }

        def obj_utilities(self):
            price = CleanText('//span[has-class("price-info")]')(self)
            if 'CC' in price:
                return UTILITIES.INCLUDED
            elif 'HC' in price:
                return UTILITIES.EXCLUDED
            else:
                return UTILITIES.UNKNOWN

        obj_station = NotAvailable
        obj_price_per_meter = PricePerMeterFilter()

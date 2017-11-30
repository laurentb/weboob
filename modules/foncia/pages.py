# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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

from __future__ import unicode_literals

import datetime

from weboob.browser.pages import JsonPage, HTMLPage, pagination
from weboob.browser.filters.standard import (CleanDecimal, CleanText, Currency,
                                             Date, Env, Format, Regexp)
from weboob.browser.filters.html import Attr, Link
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import (City, Housing, HousingPhoto, UTILITIES,
                                         ENERGY_CLASS, POSTS_TYPES,
                                         ADVERT_TYPES)
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter

from .constants import AVAILABLE_TYPES, QUERY_TYPES, QUERY_HOUSE_TYPES


class CitiesPage(JsonPage):
    def iter_cities(self):
        cities_list = self.doc
        if isinstance(self.doc, dict):
            cities_list = self.doc.values()

        for city in cities_list:
            city_obj = City()
            city_obj.id = city
            city_obj.name = city
            yield city_obj


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Format(
            '%s:%s',
            Env('type'),
            Attr('//div[boolean(@data-property-reference)]', 'data-property-reference')
        )
        obj_advert_type = ADVERT_TYPES.PROFESSIONAL

        def obj_type(self):
            type = Env('type')(self)
            if type == 'location':
                if 'appartement-meuble' in self.page.url:
                    return POSTS_TYPES.FURNISHED_RENT
                else:
                    return POSTS_TYPES.RENT
            elif type == 'achat':
                return POSTS_TYPES.SALE
            else:
                return NotAvailable

        def obj_url(self):
            return self.page.url

        def obj_house_type(self):
            url = self.obj_url()
            for house_type, types in QUERY_HOUSE_TYPES.items():
                for type in types:
                    if ('/%s/' % type) in url:
                        return house_type
            return NotAvailable

        obj_title = CleanText('//h1[has-class("OfferTop-title")]')
        obj_area = CleanDecimal(
            Regexp(
                CleanText(
                    '//div[has-class("MiniData")]//p[has-class("MiniData-item")][1]'
                ),
                r'(\d*\.*\d*) .*'
            )
        )
        obj_cost = CleanDecimal(
            '//p[has-class("OfferTop-price")]'
        )
        obj_price_per_meter = PricePerMeterFilter()
        obj_currency = Currency(
            '//p[has-class("OfferTop-price")]'
        )
        obj_location = Format(
            '%s - %s',
            CleanText('//p[@data-behat="adresseBien"]'),
            CleanText('//p[has-class("OfferTop-loc")]')
        )
        obj_text = CleanText('//div[has-class("OfferDetails-content")]/p[1]')
        obj_phone = Regexp(
            Link(
                '//a[has-class("OfferContact-btn--tel")]'
            ),
            r'tel:(.*)'
        )

        def obj_photos(self):
            photos = []
            for photo in self.xpath('//li[has-class("OfferSlider-thumbs-item")]/img'):
                photo_url = Attr('.', 'src')(photo)
                photo_url = photo_url.replace('640/480', '800/600')
                photos.append(HousingPhoto(photo_url))
            return photos

        obj_date = datetime.date.today()

        def obj_utilities(self):
            price = CleanText(
                '//p[has-class("OfferTop-price")]'
            )(self)
            if "charges comprises" in price.lower():
                return UTILITIES.INCLUDED
            else:
                return UTILITIES.EXCLUDED

        obj_rooms = CleanDecimal(
            '//div[has-class("MiniData")]//p[has-class("MiniData-item")][2]'
        )
        obj_bedrooms = CleanDecimal(
            '//div[has-class("MiniData")]//p[has-class("MiniData-item")][3]',
            default=NotAvailable
        )

        def obj_DPE(self):
            electric_consumption = CleanDecimal(Regexp(
                Attr('//div[has-class("OfferDetails-content")]//img', 'src'),
                r'https://dpe.foncia.net\/(\d+)\/.*',
                default=None
            ))(self)
            DPE = ""
            if electric_consumption is not None:
                if electric_consumption <= 50:
                    DPE = "A"
                elif 50 < electric_consumption <= 90:
                    DPE = "B"
                elif 90 < electric_consumption <= 150:
                    DPE = "C"
                elif 150 < electric_consumption <= 230:
                    DPE = "D"
                elif 230 < electric_consumption <= 330:
                    DPE = "E"
                elif 330 < electric_consumption <= 450:
                    DPE = "F"
                else:
                    DPE = "G"
            return getattr(ENERGY_CLASS, DPE, NotAvailable)

        def obj_details(self):
            details = {
                "dispo": Date(
                    Regexp(
                        CleanText('//p[has-class("OfferTop-dispo")]'),
                        r'.* (\d\d\/\d\d\/\d\d\d\d)',
                        default=datetime.date.today().isoformat()
                    )
                )(self),
                "priceMentions": CleanText('//p[has-class("OfferTop-mentions")]')(self),
                "agency": CleanText('//p[has-class("OfferContact-address")]')(self)
            }
            for item in self.xpath('//div[has-class("OfferDetails-columnize")]/div'):
                category = CleanText('./h3[has-class("OfferDetails-title--2")]')(item)
                details[category] = {}
                for detail_item in item.xpath('.//ul[has-class("List--data")]/li'):
                    detail_title = CleanText('.//span[has-class("List-data")]')(detail_item)
                    detail_value = CleanText('.//*[has-class("List-value")]')(detail_item)
                    details[category][detail_title] = detail_value
                for detail_item in item.xpath('.//ul[has-class("List--bullet")]/li'):
                    detail_title = CleanText('.')(detail_item)
                    details[category][detail_title] = True
            electric_consumption = CleanDecimal(Regexp(
                Attr('//div[has-class("OfferDetails-content")]//img', 'src'),
                r'https://dpe.foncia.net\/(\d+)\/.*',
                default=None
            ))(self)
            if electric_consumption is not None:
                details["electric_consumption"] = '{} kWhEP/m².an'.format(electric_consumption)
            else:
                details["electric_consumption"] = NotAvailable
            return details


class SearchPage(HTMLPage):
    def do_search(self, query, cities):
        form = self.get_form('//form[@name="searchForm"]')

        form['searchForm[type]'] = QUERY_TYPES.get(query.type, None)
        form['searchForm[localisation]'] = cities
        form['searchForm[type_bien][]'] = []
        for house_type in query.house_types:
            try:
                form['searchForm[type_bien][]'].extend(
                    QUERY_HOUSE_TYPES[house_type]
                )
            except KeyError:
                pass
        form['searchForm[type_bien][]'] = [
            x for x in form['searchForm[type_bien][]']
            if x in AVAILABLE_TYPES.get(query.type, [])
        ]
        if query.area_min:
            form['searchForm[surface_min]'] = query.area_min
        if query.area_max:
            form['searchForm[surface_max]'] = query.area_max
        if query.cost_min:
            form['searchForm[prix_min]'] = query.cost_min
        if query.cost_max:
            form['searchForm[prix_max]'] = query.cost_max
        if query.nb_rooms:
            form['searchForm[pieces]'] = [i for i in range(1, query.nb_rooms + 1)]
        form.submit()

    def find_housing(self, query_type, housing):
        form = self.get_form('//form[@name="searchForm"]')
        form['searchForm[type]'] = query_type
        form['searchForm[reference]'] = housing
        form.submit()


class SearchResultsPage(HTMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = '//article[has-class("TeaserOffer")]'

        next_page = Link('//div[has-class("Pagination--more")]/a[contains(text(), "Suivant")]')

        class item(ItemElement):
            klass = Housing

            obj_id = Format(
                '%s:%s',
                Env('type'),
                Attr('.//span[boolean(@data-reference)]', 'data-reference')
            )
            obj_url = AbsoluteLink('.//h3[has-class("TeaserOffer-title")]/a')
            obj_type = Env('query_type')
            obj_advert_type = ADVERT_TYPES.PROFESSIONAL

            def obj_house_type(self):
                url = self.obj_url()
                for house_type, types in QUERY_HOUSE_TYPES.items():
                    for type in types:
                        if ('/%s/' % type) in url:
                            return house_type
                return NotAvailable

            obj_title = CleanText('.//h3[has-class("TeaserOffer-title")]')
            obj_area = CleanDecimal(
                Regexp(
                    CleanText(
                        './/div[has-class("MiniData")]//p[@data-behat="surfaceDesBiens"]'
                    ),
                    r'(\d*\.*\d*) .*'
                )
            )
            obj_cost = CleanDecimal(
                './/strong[has-class("TeaserOffer-price-num")]'
            )
            obj_price_per_meter = PricePerMeterFilter()
            obj_currency = Currency(
                './/strong[has-class("TeaserOffer-price-num")]'
            )
            obj_location = CleanText('.//p[has-class("TeaserOffer-loc")]')
            obj_text = CleanText('.//p[has-class("TeaserOffer-description")]')

            def obj_photos(self):
                url = CleanText(Attr('.//a[has-class("TeaserOffer-ill")]/img', 'src'))(self)
                # If the used photo is a default no photo, the src is on the same domain.
                if url[0] == '/':
                    return []
                else:
                    return [HousingPhoto(url)]

            obj_date = datetime.date.today()

            def obj_utilities(self):
                price = CleanText(
                    './/strong[has-class("TeaserOffer-price-num")]'
                )(self)
                if "charges comprises" in price.lower():
                    return UTILITIES.INCLUDED
                else:
                    return UTILITIES.EXCLUDED

            obj_rooms = CleanDecimal(
                './/div[has-class("MiniData")]//p[@data-behat="nbPiecesDesBiens"]',
                default=NotAvailable
            )
            obj_bedrooms = CleanDecimal(
                './/div[has-class("MiniData")]//p[@data-behat="nbChambresDesBiens"]',
                default=NotAvailable
            )

            def obj_details(self):
                return {
                    "dispo": Date(
                        Attr('.//span[boolean(@data-dispo)]', 'data-dispo',
                             default=datetime.date.today().isoformat())
                    )(self),
                    "priceMentions": CleanText('.//span[has-class("TeaserOffer-price-mentions")]')(self)
                }

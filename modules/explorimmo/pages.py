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
from __future__ import unicode_literals

import json
import math
import re
from decimal import Decimal
from datetime import datetime
from weboob.browser.filters.json import Dict
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.pages import JsonPage, HTMLPage, pagination
from weboob.browser.filters.standard import (CleanText, CleanDecimal, Currency,
                                             Regexp, Env, BrowserURL, Filter,
                                             Format)
from weboob.browser.filters.html import Attr, CleanHTML, XPath
from weboob.capabilities.base import NotAvailable, NotLoaded, Currency as BaseCurrency
from weboob.capabilities.housing import (Housing, HousingPhoto, City,
                                         UTILITIES, ENERGY_CLASS, POSTS_TYPES,
                                         ADVERT_TYPES, HOUSE_TYPES)
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.tools.compat import unquote


class CitiesPage(JsonPage):

    ENCODING = 'UTF-8'

    def build_doc(self, content):
        content = super(CitiesPage, self).build_doc(content)
        if content:
            return content
        else:
            return [{"locations": []}]

    @method
    class get_cities(DictElement):
        item_xpath = '0/locations'

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
            js_datas = CleanText(
                '//div[@id="js-data"]/@data-rest-search-request'
            )(self).split('?')[-1].split('&')

            try:
                resultsPerPage = next(
                    x for x in js_datas if 'resultsPerPage' in x
                ).split('=')[-1]
                currentPageNumber = next(
                    x for x in js_datas if 'currentPageNumber' in x
                ).split('=')[-1]
                resultCount = CleanText(
                    '(//div[@id="js-data"]/@data-result-count)[1]'
                )(self)
                totalPageNumber = math.ceil(
                    int(resultCount) / int(resultsPerPage)
                )

                next_page = int(currentPageNumber) + 1
                if next_page <= totalPageNumber:
                    return self.page.url.replace(
                        'page=%s' % currentPageNumber,
                        'page=%d' % next_page
                    )
            except StopIteration:
                pass

        class item(ItemElement):
            klass = Housing

            def is_agency(self):
                agency = CleanText('.//span[has-class("item-agency-name")]')(self.el)
                return 'annonce de particulier' not in agency.lower()

            def condition(self):
                if len(self.env['advert_types']) == 1:
                    is_agency = self.is_agency()
                    if self.env['advert_types'][0] == ADVERT_TYPES.PERSONAL:
                        return not is_agency
                    elif self.env['advert_types'][0] == ADVERT_TYPES.PROFESSIONAL:
                        return is_agency
                return Attr('.', 'data-classified-id', default=False)(self)

            obj_id = Attr('.', 'data-classified-id')
            obj_type = Env('query_type')

            def obj_advert_type(self):
                if self.is_agency():
                    return ADVERT_TYPES.PROFESSIONAL
                else:
                    return ADVERT_TYPES.PERSONAL

            def obj_house_type(self):
                type = self.obj_title(self).split()[0].lower()
                if type == "appartement" or type == "studio" or type == "chambre":
                    return HOUSE_TYPES.APART
                elif type == "maison" or type == "villa":
                    return HOUSE_TYPES.HOUSE
                elif type == "parking":
                    return HOUSE_TYPES.PARKING
                elif type == "terrain":
                    return HOUSE_TYPES.LAND
                else:
                    return HOUSE_TYPES.OTHER

            obj_title = CleanText('.//*[has-class("js-item-title")]')

            def obj_location(self):
                script = CleanText('./script')(self)
                try:
                    # Should be standard JSON+LD data
                    script = json.loads(script)
                except ValueError:
                    try:
                        # But explorimmo can't write JSON correctly and there
                        # is a trailing "}"
                        script = json.loads(script.strip().rstrip('}'))
                    except ValueError:
                        script = None
                if not script:
                    return NotAvailable

                try:
                    return '%s (%s)' % (
                        script['address']['addressLocality'],
                        script['address']['postalCode']
                    )
                except (KeyError):
                    return NotAvailable

            def obj_cost(self):
                selector = './div/div/span[@class="price-label"]|./div/div[@class="item-price-pdf"]|./div/div/span[@class="item-price"]'
                cost = CleanDecimal(Regexp(CleanText(selector, default=''),
                                           r'de (.*) à .*',
                                           default=0))(self)
                if cost == 0:
                    return CleanDecimal(selector, default=NotAvailable)(self)
                else:
                    return cost

            obj_currency = Currency(
                './div/div/span[@class="price-label"]|./div/div[@class="item-price-pdf"]|./div/div/span[@class="item-price"]'
            )

            def obj_utilities(self):
                utilities = CleanText(
                    './div/div/span[@class="price-label"]|'
                    './div/div[@class="item-price-pdf"]|'
                    './div/div/span[@class="item-price"]'
                )(self)
                if "CC" in utilities:
                    return UTILITIES.INCLUDED
                else:
                    return UTILITIES.UNKNOWN

            obj_text = CleanText('./div/div/div[@itemprop="description"]')
            obj_area = CleanDecimal(
                Regexp(
                    obj_title,
                    r'(.*?)([\d,\.]*) m2(.*?)',
                    '\\2',
                    default=None
                ),
                replace_dots=True,
                default=NotAvailable
            )

            obj_url = Format(
                "http://www.explorimmo.com/annonce-%s.html",
                CleanText('./@data-classified-id')
            )

            obj_price_per_meter = PricePerMeterFilter()

            def obj_phone(self):
                phone = CleanText('./div/div/ul/li[has-class("js-clickphone")]',
                                  replace=[('Téléphoner : ', '')],
                                  default=NotAvailable)(self)

                if '...' in phone:
                    return NotLoaded

                return phone

            def obj_details(self):
                charges = CleanText('.//span[@class="price-fees"]',
                                    default=None)(self)
                if charges:
                    return {
                        "fees": charges.split(":")[1].strip()
                    }
                else:
                    return NotLoaded

            def obj_photos(self):
                url = Attr(
                    '.',
                    'data-img',
                    default=None
                )(self)
                if url:
                    url = unquote(url)
                    if "http://" in url[3:]:
                        rindex = url.rfind("?")
                        if rindex == -1:
                            rindex = None
                        url = url[url.find("http://", 3):rindex]
                    return [HousingPhoto(url)]
                else:
                    return NotAvailable


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

        def is_agency(self):
            return Dict('agency/isParticulier')(self) == 'false'

        obj_id = Env('_id')

        def obj_type(self):
            transaction = Dict('characteristics/transaction')(self)
            if transaction == 'location':
                if Dict('characteristics/isFurnished')(self) == True:
                    return POSTS_TYPES.FURNISHED_RENT
                else:
                    return POSTS_TYPES.RENT
            elif transaction == 'vente':
                type = Dict('characteristics/estateType')(self).lower()
                if 'viager' in type:
                    return POSTS_TYPES.VIAGER
                else:
                    return POSTS_TYPES.SALE
            else:
                return NotAvailable

        def obj_advert_type(self):
            if self.is_agency:
                return ADVERT_TYPES.PROFESSIONAL
            else:
                return ADVERT_TYPES.PERSONAL

        def obj_house_type(self):
            type = Dict('characteristics/estateType')(self).lower()
            if 'appartement' in type:
                return HOUSE_TYPES.APART
            elif 'maison' in type:
                return HOUSE_TYPES.HOUSE
            elif 'parking' in type:
                return HOUSE_TYPES.PARKING
            elif 'terrain' in type:
                return HOUSE_TYPES.LAND
            else:
                return HOUSE_TYPES.OTHER

        obj_title = Dict('characteristics/titleWithTransaction')
        obj_location = Format('%s %s %s', Dict('location/address'),
                              Dict('location/cityLabel'),
                              Dict('location/postalCode'))

        def obj_cost(self):
            cost = TypeDecimal(Dict('characteristics/price'))(self)
            if cost == 0:
                cost = TypeDecimal(Dict('characteristics/priceMin'))(self)
            return cost

        obj_currency = BaseCurrency.get_currency('€')

        def obj_utilities(self):
            are_fees_included = Dict('characteristics/areFeesIncluded',
                                     default=None)(self)
            if are_fees_included:
                return UTILITIES.INCLUDED
            else:
                return UTILITIES.EXCLUDED

        obj_text = CleanHTML(Dict('characteristics/description'))
        obj_url = BrowserURL('housing_html', _id=Env('_id'))

        def obj_area(self):
            area = TypeDecimal(Dict('characteristics/area'))(self)
            if area == 0:
                area = TypeDecimal(Dict('characteristics/areaMin'))(self)
            return area

        obj_date = FromTimestamp(Dict('characteristics/date'))
        obj_bedrooms = TypeDecimal(Dict('characteristics/bedroomCount'))

        def obj_rooms(self):
            # TODO: Why is roomCount a list?
            rooms = Dict('characteristics/roomCount', default=[])(self)
            if rooms:
                return TypeDecimal(rooms[0])(self)
            return NotAvailable

        obj_price_per_meter = PricePerMeterFilter()

        def obj_photos(self):
            photos = []
            for img in Dict('characteristics/images')(self):
                m = re.search('http://thbr\.figarocms\.net.*(http://.*)', img.get('xl'))
                if m:
                    photos.append(HousingPhoto(m.group(1)))
                else:
                    photos.append(HousingPhoto(img.get('xl')))
            return photos

        def obj_DPE(self):
            DPE = Dict(
                'characteristics/energyConsumptionCategory',
                default=""
            )(self)
            return getattr(ENERGY_CLASS, DPE, NotAvailable)

        def obj_GES(self):
            GES = Dict(
                'characteristics/greenhouseGasEmissionCategory',
                default=""
            )(self)
            return getattr(ENERGY_CLASS, GES, NotAvailable)

        def obj_details(self):
            details = {}
            details['fees'] = Dict(
                'characteristics/fees', default=NotAvailable
            )(self)
            details['agencyFees'] = Dict(
                'characteristics/agencyFees', default=NotAvailable
            )(self)
            details['guarantee'] = Dict(
                'characteristics/guarantee', default=NotAvailable
            )(self)
            details['bathrooms'] = Dict(
                'characteristics/bathroomCount', default=NotAvailable
            )(self)
            details['creationDate'] = FromTimestamp(
                                          Dict(
                                              'characteristics/creationDate', default=NotAvailable
                                          ),
                                          default=NotAvailable
            )(self)
            details['availabilityDate'] = Dict(
                'characteristics/estateAvailabilityDate', default=NotAvailable
            )(self)
            details['exposure'] = Dict(
                'characteristics/exposure', default=NotAvailable
            )(self)
            details['heatingType'] = Dict(
                'characteristics/heatingType', default=NotAvailable
            )(self)
            details['floor'] = Dict(
                'characteristics/floor', default=NotAvailable
            )(self)
            details['bedrooms'] = Dict(
                'characteristics/bedroomCount', default=NotAvailable
            )(self)
            details['isFurnished'] = Dict(
                'characteristics/isFurnished', default=NotAvailable
            )(self)
            rooms = Dict('characteristics/roomCount', default=[])(self)
            if len(rooms):
                details['rooms'] = rooms[0]
            details['available'] = Dict(
                'characteristics/isAvailable', default=NotAvailable
            )(self)
            agency = Dict('agency', default=NotAvailable)(self)
            details['agency'] = ', '.join([
                x for x in [
                    agency.get('corporateName', ''),
                    agency.get('corporateAddress', ''),
                    agency.get('corporatePostalCode', ''),
                    agency.get('corporateCity', '')
                ] if x
            ])
            return details

    def get_total_page(self):
        return self.doc.get('pagination').get('total') if 'pagination' in self.doc else 0


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_title = CleanText('//h1[@itemprop="name"]')
        obj_location = CleanText('//span[@class="informations-localisation"]')
        obj_cost = CleanDecimal('//span[@itemprop="price"]')
        obj_currency = Currency('//span[@itemprop="price"]')
        obj_text = CleanHTML('//div[@itemprop="description"]')
        obj_url = BrowserURL('housing', _id=Env('_id'))
        obj_area = CleanDecimal(Regexp(CleanText('//h1[@itemprop="name"]'),
                                       r'(.*?)(\d*) m2(.*?)', '\\2'), default=NotAvailable)
        obj_price_per_meter = PricePerMeterFilter()

        def obj_photos(self):
            photos = []
            for img in XPath('//a[@class="thumbnail-link"]/img[@itemprop="image"]')(self):
                url = Regexp(CleanText('./@src'), r'http://thbr\.figarocms\.net.*(http://.*)')(img)
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

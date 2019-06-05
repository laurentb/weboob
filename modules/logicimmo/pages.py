# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (Currency, Format, CleanText,
                                             Regexp, CleanDecimal, Date, Env,
                                             BrowserURL)
from weboob.browser.filters.html import Attr, XPath, CleanHTML
from weboob.capabilities.housing import (Housing, HousingPhoto, City,
                                         UTILITIES, ENERGY_CLASS, POSTS_TYPES,
                                         ADVERT_TYPES, HOUSE_TYPES)
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.tools.compat import urljoin


class CitiesPage(JsonPage):
    @method
    class get_cities(DictElement):
        item_xpath = '*/children'

        class item(ItemElement):
            klass = City

            def condition(self):
                return Dict('lct_parent_id')(self) != '0'

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

        def obj_type(self):
            url = BrowserURL('housing', _id=Env('_id'))(self)
            if 'colocation' in url:
                return POSTS_TYPES.SHARING
            elif 'location' in url:
                isFurnished = False
                for li in XPath('//ul[@itemprop="description"]/li')(self):
                    label = CleanText('./span[has-class("criteria-label")]')(li)
                    if label.lower() == "meublé":
                        isFurnished = (
                            CleanText('./span[has-class("criteria-value")]')(li).lower() == 'oui'
                        )
                if isFurnished:
                    return POSTS_TYPES.FURNISHED_RENT
                else:
                    return POSTS_TYPES.RENT
            elif 'vente' in url:
                offertype = Attr(
                    '//button[has-class("offer-contact-vertical-phone")][1]',
                    'data-offertransactiontype'
                )(self)
                if offertype == '4':
                    return POSTS_TYPES.VIAGER
                else:
                    return POSTS_TYPES.SALE
            return NotAvailable
        obj_advert_type = ADVERT_TYPES.PROFESSIONAL

        def obj_house_type(self):
            house_type = CleanText('.//div[has-class("offer-type")]')(self).lower()
            if house_type == "appartement":
                return HOUSE_TYPES.APART
            elif house_type == "maison":
                return HOUSE_TYPES.HOUSE
            elif house_type == "terrain":
                return HOUSE_TYPES.LAND
            elif house_type == "parking":
                return HOUSE_TYPES.PARKING
            else:
                return HOUSE_TYPES.OTHER

        obj_title = CleanText(CleanHTML('//meta[@itemprop="name"]/@content'))
        obj_area = CleanDecimal(Regexp(CleanText(CleanHTML('//meta[@itemprop="name"]/@content')),
                                       '(.*?)(\d*) m\xb2(.*?)', '\\2', default=NotAvailable),
                                default=NotAvailable)
        obj_rooms = CleanDecimal('//div[has-class("offer-info")]//span[has-class("offer-rooms-number")]',
                                 default=NotAvailable)
        obj_cost = CleanDecimal('//*[@itemprop="price"]', default=0)
        obj_currency = Currency(
            '//*[@itemprop="price"]'
        )

        def obj_utilities(self):
            notes = CleanText('//p[@class="offer-description-notes"]')(self)
            if "Loyer mensuel charges comprises" in notes:
                return UTILITIES.INCLUDED
            else:
                return UTILITIES.UNKNOWN

        obj_price_per_meter = PricePerMeterFilter()
        obj_date = Date(Regexp(CleanText('//p[@class="offer-description-notes"]|//p[has-class("darkergrey")]'),
                               u'.* Mis à jour : (\d{2}/\d{2}/\d{4}).*'),
                        dayfirst=True)
        obj_text = CleanHTML('//div[has-class("offer-description-text")]/meta[@itemprop="description"]/@content')
        obj_location = CleanText('//*[@itemprop="address"]')
        obj_station = CleanText(
            '//div[has-class("offer-description-metro")]',
            default=NotAvailable
        )

        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_photos(self):
            photos = []
            for img in XPath('//div[has-class("carousel-content")]//img/@src')(self):
                url = u'%s' % img.replace('75x75', '800x600')
                url = urljoin(self.page.url, url)  # Ensure URL is absolute
                photos.append(HousingPhoto(url))
            return photos

        def obj_DPE(self):
            energy_value = CleanText(
                '//div[has-class("offer-energy-greenhouseeffect-summary")]//div[has-class("energy-summary")]',
                default=""
            )(self)
            if len(energy_value):
                energy_value = energy_value.replace("DPE", "").strip()[0]
            return getattr(ENERGY_CLASS, energy_value, NotAvailable)

        def obj_GES(self):
            greenhouse_value = CleanText(
                '//div[has-class("offer-energy-greenhouseeffect-summary")]//div[has-class("greenhouse-summary")]',
                default=""
            )(self)
            if len(greenhouse_value):
                greenhouse_value = greenhouse_value.replace("GES", "").strip()[0]
            return getattr(ENERGY_CLASS, greenhouse_value, NotAvailable)

        def obj_details(self):
            details = {}

            details["creationDate"] = Date(
                Regexp(
                    CleanText(
                        '//p[@class="offer-description-notes"]|//p[has-class("darkergrey")]'
                    ),
                    u'.*Mis en ligne : (\d{2}/\d{2}/\d{4}).*'
                ),
                dayfirst=True
            )(self)

            honoraires = CleanText(
                (
                    '//div[has-class("offer-price")]/span[has-class("lbl-agencyfees")]'
                ),
                default=None
            )(self)
            if honoraires:
                details["Honoraires"] = (
                    "{} (TTC, en sus)".format(
                        honoraires.split(":")[1].strip()
                    )
                )

            for li in XPath('//ul[@itemprop="description"]/li')(self):
                label = CleanText('./span[has-class("criteria-label")]')(li)
                value = CleanText('./span[has-class("criteria-value")]')(li)
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
    class iter_sharing(ListElement):
        item_xpath = '//article[has-class("offer-block")]'

        class item(ItemElement):
            klass = Housing

            obj_id = Format('colocation-%s', CleanText('./div/header/@id', replace=[('header-offer-', '')]))
            obj_type = POSTS_TYPES.SHARING
            obj_advert_type = ADVERT_TYPES.PROFESSIONAL
            obj_title = CleanText(CleanHTML('./div/header/section/p[@class="property-type"]/span/@title'))

            obj_area = CleanDecimal('./div/header/section/p[@class="offer-attributes"]/a/span[@class="offer-area-number"]',
                                    default=0)

            obj_cost = CleanDecimal('./div/header/section/p[@class="price"]', default=0)
            obj_currency = Currency(
                './div/header/section/p[@class="price"]'
            )
            obj_utilities = UTILITIES.UNKNOWN

            obj_text = CleanText(
                './div/div[@class="content-offer"]/section[has-class("content-desc")]/p/span[has-class("offer-text")]/@title',
                default=NotLoaded
            )

            obj_date = Date(Regexp(CleanText('./div/header/section/p[has-class("update-date")]'),
                                   ".*(\d{2}/\d{2}/\d{4}).*"))

            obj_location = CleanText(
                '(./div/div[@class="content-offer"]/section[has-class("content-desc")]/p)[1]/span/@title',
                default=NotLoaded
            )

    @method
    class iter_housings(ListElement):
        item_xpath = '//div[has-class("offer-block")]'

        class item(ItemElement):
            offer_details_wrapper = (
                './/div[has-class("offer-details-wrapper")]'
            )
            klass = Housing

            obj_id = Format(
                '%s-%s',
                Regexp(Env('type'), '(.*)-.*'),
                CleanText('./@id', replace=[('header-offer-', '')])
            )
            obj_type = Env('query_type')
            obj_advert_type = ADVERT_TYPES.PROFESSIONAL

            def obj_house_type(self):
                house_type = CleanText('.//div[has-class("offer-details-type")]/a')(self).split(' ')[0].lower()
                if house_type == "appartement":
                    return HOUSE_TYPES.APART
                elif house_type == "maison":
                    return HOUSE_TYPES.HOUSE
                elif house_type == "terrain":
                    return HOUSE_TYPES.LAND
                elif house_type == "parking":
                    return HOUSE_TYPES.PARKING
                else:
                    return HOUSE_TYPES.OTHER

            obj_title = CleanText('.//div[has-class("offer-details-type")]/a/@title')

            obj_url = Format(u'%s%s',
                             CleanText('.//div/a[@class="offer-link"]/@href'),
                             CleanText('.//div/a[@class="offer-link"]/\
@data-orpi', default=""))

            obj_area = CleanDecimal(
                (
                    offer_details_wrapper +
                    '/div/div/div[has-class("offer-details-second")]' +
                    '/div/h3[has-class("offer-attributes")]/span' +
                    '/span[has-class("offer-area-number")]'
                ),
                default=NotLoaded
            )
            obj_rooms = CleanDecimal(
                (
                    offer_details_wrapper +
                    '/div/div/div[has-class("offer-details-second")]' +
                    '/div/h3[has-class("offer-attributes")]' +
                    '/span[has-class("offer-rooms")]' +
                    '/span[has-class("offer-rooms-number")]'
                ),
                default=NotAvailable
            )
            obj_cost = CleanDecimal(
                Regexp(
                    CleanText(
                        (
                            offer_details_wrapper +
                            '/div/p[@class="offer-price"]/span'
                        ),
                        default=NotLoaded
                    ),
                    '(.*) [%s%s%s]' % (u'€', u'$', u'£'),
                    default=NotLoaded
                ),
                default=NotLoaded
            )
            obj_currency = Currency(
                offer_details_wrapper + '/div/p[has-class("offer-price")]/span'
            )
            obj_price_per_meter = PricePerMeterFilter()
            obj_utilities = UTILITIES.UNKNOWN
            obj_text = CleanText(
                offer_details_wrapper + '/div/div/div/p[has-class("offer-description")]/span'
            )
            obj_location = CleanText(
                offer_details_wrapper + '/div[@class="offer-details-location"]',
                replace=[('Voir sur la carte','')]
            )

            def obj_photos(self):
                photos = []
                url = Attr(
                    './/div[has-class("offer-picture")]//img',
                    'src'
                )(self)
                if url:
                    url = url.replace('400x267', '800x600')
                    url = urljoin(self.page.url, url)  # Ensure URL is absolute
                    photos.append(HousingPhoto(url))
                return photos

            def obj_details(self):
                details = {}
                honoraires = CleanText(
                    (
                        self.offer_details_wrapper +
                        '/div/div/p[@class="offer-agency-fees"]'
                    ),
                    default=None
                )(self)
                if honoraires:
                    details["Honoraires"] = (
                        "{} (TTC, en sus)".format(
                            honoraires.split(":")[1].strip()
                        )
                    )
                return details

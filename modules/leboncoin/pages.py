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

from weboob.browser.pages import HTMLPage, pagination, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, Env, DateTime, BrowserURL, Format, Join
from weboob.browser.filters.javascript import JSVar
from weboob.browser.filters.html import Attr, Link
from weboob.browser.filters.json import Dict
from weboob.capabilities.housing import (City, Housing, HousingPhoto, Query,
                                         UTILITIES, ENERGY_CLASS)
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.tools.date import DATE_TRANSLATE_FR, LinearDateGuesser
from weboob.tools.compat import unicode

from decimal import Decimal
from datetime import date, timedelta
import re
from lxml import etree


class CityListPage(HTMLPage):

    def build_doc(self, content):
        content = super(CityListPage, self).build_doc(content)
        if content.getroot() is not None:
            return content
        return etree.Element("html")

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

    ENCODING = 'iso-8859-1'

    def get_area_min(self, asked_area):
        return self.find_select_value(asked_area, '//select[@id="sqs"]/option')

    def get_area_max(self, asked_area):
        return self.find_select_value(asked_area, '//select[@id="sqe"]/option')

    def get_rooms_min(self, asked_rooms):
        return self.find_select_value(asked_rooms, '//select[@id="rooms_ros"]/option')

    # def get_rooms_max(self, asked_rooms):
    #     return self.find_select_value(asked_rooms, '//select[@id="roe"]/option')

    def get_cost_min(self, asked_cost, _type):
        _id = "ps" if _type == Query.TYPE_SALE else "mrs"
        return self.find_select_value(asked_cost, '//select[@id="%s"]/option' % _id)

    def get_cost_max(self, asked_cost, _type):
        _id = "pe" if _type == Query.TYPE_SALE else "mre"
        return self.find_select_value(asked_cost, '//select[@id="%s"]/option' % _id)

    def find_select_value(self, ref_value, selector):
        select = {}
        for item in self.doc.xpath(selector):
            if item.attrib['value']:
                select[CleanDecimal('.')(item)] = CleanDecimal('./@value')(item)

        select_keys = sorted(select.keys())
        for select_value in select_keys:
            if select_value >= ref_value:
                return select[select_value]

        return select[select_keys[-1]] if select else 0

    @pagination
    @method
    class get_housing_list(ListElement):
        item_xpath = '//a[has-class("list_item")]'

        next_page = Format(u'http:%s', Link('//a[@id="next"]'))

        class item(ItemElement):
            klass = Housing

            def validate(self, obj):
                return obj.id is not None

            obj_url = Format(u'http:%s', Link('.'))
            obj_id = Regexp(Link('.'),
                            '//www.leboncoin.fr/(ventes_immobilieres|locations|colocations)/(.*).htm.*',
                            '\\2', default=None)

            obj_title = CleanText('./@title|./section/p[@class="item_title"]')
            obj_cost = CleanDecimal('./section[@class="item_infos"]/*[@class="item_price"]/text()',
                                    replace_dots=(',', '.'),
                                    default=Decimal(0))
            obj_location = CleanText(
                './section[@class="item_infos"]/*[@itemtype="http://schema.org/Place"]/text()'
            )
            obj_currency = Regexp(CleanText('./section[@class="item_infos"]/*[@class="item_price"]'),
                                  '\d+ ([%s%s%s]).*' % (u'€', u'$', u'£'), default=u'€')

            def obj_utilities(self):
                utilities = Regexp(CleanText('./section[@class="item_infos"]/*[@class="item_price"]'),
                                   '\d+ [%s%s%s](.*)' % (u'€', u'$', u'£'),
                                   default=u'')(self)
                if "C.C." in utilities:
                    return UTILITIES.INCLUDED
                elif "H.C." in utilities:
                    return UTILITIES.EXCLUDED
                else:
                    return UTILITIES.UNKNOWN

            obj_text = Join(' - ', './/p[@class="item_supp"]')

            def obj_date(self):
                _date = CleanText('./section[@class="item_infos"]/aside/p[@class="item_supp"]/text()',
                                  replace=[('Aujourd\'hui', str(date.today())),
                                           ('Hier', str((date.today() - timedelta(1))))])(self)

                if not _date:
                    return NotAvailable

                for fr, en in DATE_TRANSLATE_FR:
                    _date = fr.sub(en, _date)

                self.env['tmp'] = _date
                return DateTime(Env('tmp'), LinearDateGuesser())(self)

            def obj_photos(self):
                photos = []
                url = Attr(
                    './div[@class="item_image"]/span/span[@class="lazyload"]',
                    'data-imgsrc',
                    default=None
                )(self)
                if url:
                    photos.append(
                        HousingPhoto(
                            "https:{}".format(
                                url.replace("ad-thumb", "ad-image")
                            )
                        )
                    )
                return photos


class HousingPage(HTMLPage):

    ENCODING = 'iso-8859-1'

    def get_api_key(self):
        return JSVar(CleanText('//script'),
                     var='apiKey',
                     default=None)(self.doc)

    @method
    class get_housing(ItemElement):
        klass = Housing

        def parse(self, el):
            details = dict()
            self.env['area'] = NotAvailable
            self.env['GES'] = NotAvailable
            self.env['DPE'] = NotAvailable
            for item in el.xpath('//div[@class="line"]/h2'):
                if 'Surface' in CleanText('./span[@class="property"]')(item):
                    self.env['area'] = CleanDecimal(Regexp(CleanText('./span[@class="value"]'), '(.*)m.*'),
                                                    replace_dots=(',', '.'))(item)

                else:
                    key = u'%s' % CleanText('./span[@class="property"]')(item)
                    if 'GES' in key or 'Classe' in key:
                        if 'Classe' in key:
                            key = 'DPE'

                        value = (
                            CleanText('./span[@class="value"]')(item).strip()
                        )
                        if len(value):
                            self.env[key] = getattr(ENERGY_CLASS, value[0],
                                            NotAvailable)
                    else:
                        details[key] = CleanText('./span[@class="value"]')(item)

            self.env['details'] = details

        obj_id = Env('_id')
        obj_title = CleanText('//h1[@itemprop="name"]')
        obj_cost = CleanDecimal('//h2[@itemprop="price"]/@content', default=Decimal(0))

        obj_currency = Regexp(
            CleanText(
                '//h2[@itemprop="price"]/span[@class="value"]'
            ),
            '.*([%s%s%s])' % (u'€', u'$', u'£'),
            default=u'€'
        )

        def obj_utilities(self):
            utilities = Regexp(
                CleanText(
                    '//h2[@itemprop="price"]/span[@class="value"]'
                ),
                '.*[%s%s%s](.*)' % (u'€', u'$', u'£'),
                default=u''
            )(self)
            if "C.C." in utilities:
                return UTILITIES.INCLUDED
            elif "H.C." in utilities:
                return UTILITIES.EXCLUDED
            else:
                return UTILITIES.UNKNOWN

        obj_DPE = Env('DPE')
        obj_GES = Env('GES')

        obj_text = CleanText('//p[@itemprop="description"]')
        obj_location = CleanText('//span[@itemprop="address"]')
        obj_details = Env('details')

        def obj_rooms(self):
            rooms = int(self.env["details"].get(u"Pièces", -1))
            return NotAvailable if rooms == -1 else rooms

        obj_area = Env('area')
        obj_price_per_meter = PricePerMeterFilter()
        obj_url = BrowserURL('housing', _id=Env('_id'))

        def obj_date(self):
            _date = Regexp(CleanText('//p[has-class("line")]', replace=[(u'à', '')]),
                           '.*Mise en ligne le (.*)')(self)

            for fr, en in DATE_TRANSLATE_FR:
                _date = fr.sub(en, _date)

            self.env['tmp'] = _date
            return DateTime(Env('tmp'), LinearDateGuesser())(self)

        def obj_photos(self):
            items = re.findall(r'images\[\d\]\s*=\s*"([\w:\/\.-]*\.jpg)";',
                               CleanText('//script')(self))
            photos = [HousingPhoto(unicode(item)) for item in items]
            if not photos:
                img = CleanText('//meta[@itemprop="image"]/@content',
                                default=None)(self)
                if img:
                    photos.append(HousingPhoto(img))

            return photos


# TODO
class PhonePage(JsonPage):
    def get_phone(self):
        if Dict('utils/status')(self.doc) == u'OK':
            return Dict('utils/phonenumber')(self.doc)
        return NotAvailable

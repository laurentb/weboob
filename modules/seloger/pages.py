# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from weboob.browser.pages import JsonPage, pagination, HTMLPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import XPath
from weboob.browser.filters.standard import (CleanText, CleanDecimal, Currency,
                                             Env, Regexp, Field, BrowserURL)
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.capabilities.housing import (Housing, HousingPhoto, City,
                                         UTILITIES, ENERGY_CLASS, POSTS_TYPES,
                                         ADVERT_TYPES)
from weboob.capabilities.address import PostalAddress
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.tools.json import json
from weboob.exceptions import ActionNeeded
from .constants import TYPES, RET
import codecs


class ErrorPage(HTMLPage):
    def on_load(self):
        raise ActionNeeded("Please resolve the captcha")


class CitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        ignore_duplicate = True

        class item(ItemElement):
            klass = City

            obj_id = Dict('Params/ci')
            obj_name = Dict('Display')


class SearchResultsPage(HTMLPage):
    def __init__(self, *args, **kwargs):
        HTMLPage.__init__(self, *args, **kwargs)
        json_content = Regexp(CleanText('//script'),
                              r"window\[\"initialData\"\] = JSON.parse\(\"({.*})\"\);window\[\"tags\"\]")(self.doc)
        json_content = codecs.unicode_escape_decode(json_content)[0]
        json_content = json_content.encode('utf-8', 'surrogatepass').decode('utf-8')
        self.doc = json.loads(json_content)

    @pagination
    @method
    class iter_housings(DictElement):
        item_xpath = 'cards/list'

        def next_page(self):
            page_nb = Dict('navigation/pagination/page')(self)
            max_results = Dict('navigation/pagination/maxResults')(self)
            results_per_page = Dict('navigation/pagination/resultsPerPage')(self)

            if int(max_results) / int(results_per_page) > int(page_nb):
                return BrowserURL('search', query=Env('query'), page_number=int(page_nb) + 1)(self)

        # TODO handle bellesdemeures

        class item(ItemElement):
            klass = Housing

            def condition(self):
                return Dict('cardType')(self) not in ['advertising', 'localExpert'] and Dict('id', default=False)(self)

            obj_id = Dict('id')

            def obj_type(self):
                idType = int(Env('query_type')(self))
                type = next(k for k, v in TYPES.items() if v == idType)
                if type == POSTS_TYPES.FURNISHED_RENT:
                    # SeLoger does not let us discriminate between furnished and not furnished.
                    return POSTS_TYPES.RENT
                return type

            def obj_title(self):
                return "{} - {} - {}".format(Dict('estateType')(self),
                                             " / ".join(Dict('tags')(self)),
                                             Field('location')(self))

            def obj_advert_type(self):
                is_agency = Dict('contact/agencyId', default=False)(self)
                if is_agency:
                    return ADVERT_TYPES.PROFESSIONAL
                else:
                    return ADVERT_TYPES.PERSONAL

            obj_utilities = UTILITIES.EXCLUDED

            def obj_photos(self):
                photos = []
                for photo in Dict('photos')(self):
                    photos.append(HousingPhoto(photo))
                return photos

            def obj_location(self):
                quartier = Dict('districtLabel')(self)
                quartier = quartier if quartier else ''
                ville = Dict('cityLabel')(self)
                ville = ville if ville else ''
                cp = Dict('zipCode')(self)
                cp = cp if cp else ''
                return u'%s %s (%s)' % (quartier, ville, cp)

            obj_url = Dict('classifiedURL')

            obj_text = Dict('description')

            obj_cost = CleanDecimal(Dict('pricing/price', default=NotLoaded), default=NotLoaded)
            obj_currency = Currency(Dict('pricing/price', default=NotLoaded), default=NotLoaded)
            obj_price_per_meter = CleanDecimal(Dict('pricing/squareMeterPrice'), default=PricePerMeterFilter)


class HousingPage(HTMLPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        def parse(self, el):
            json_content = Regexp(CleanText('//script'), "var ava_data = ({.+?});")(self)
            json_content = json_content.replace("logged", "\"logged\"")
            json_content = json_content.replace("lengthcarrousel", "\"lengthcarrousel\"")
            json_content = json_content.replace("products", "\"products\"")
            json_content = json_content.replace("// // ANNONCES_SIMILAIRE / RECO", "")
            self.house_json_datas = json.loads(json_content)['products'][0]

        obj_id = CleanText('//form[@name="central"]/input[@name="idannonce"]/@value')

        def obj_house_type(self):
            naturebien = CleanText('//form[@name="central"]/input[@name="naturebien"]/@value')(self)
            try:
                return next(k for k, v in RET.items() if v == naturebien)
            except StopIteration:
                return NotLoaded

        def obj_type(self):
            idType = int(CleanText('//form[@name="central"]/input[@name="idtt"]/@value')(self))
            type = next(k for k, v in TYPES.items() if v == idType)
            if type == POSTS_TYPES.FURNISHED_RENT:
                # SeLoger does not let us discriminate between furnished and not furnished.
                return POSTS_TYPES.RENT
            return type

        def obj_advert_type(self):
            is_agency = (
                CleanText('//form[@name="central"]/input[@name="nomagance"]/@value')(self) or
                CleanText('//form[@name="central"]/input[@name="urlagence"]/@value')(self) or
                CleanText('//form[@name="central"]/input[@name="adresseagence"]/@value')(self)
            )
            if is_agency:
                return ADVERT_TYPES.PROFESSIONAL
            else:
                return ADVERT_TYPES.PERSONAL

        def obj_photos(self):
            photos = []

            for photo in XPath('//div[@class="carrousel_slide"]/img/@src')(self):
                photos.append(HousingPhoto("https:{}".format(photo)))

            for photo in XPath('//div[@class="carrousel_slide"]/@data-lazy')(self):
                p = json.loads(photo)
                photos.append(HousingPhoto("https:{}".format(p['url'])))

            return photos

        obj_title = CleanText('//title[1]')

        def obj_location(self):
            quartier = Regexp(CleanText('//script'),
                              r"'nomQuartier', { value: \"([\w -]+)\", ")(self)
            ville = CleanText('//form[@name="central"]/input[@name="ville"]/@value')(self)
            ville = ville if ville else ''
            cp = CleanText('//form[@name="central"]/input[@name="codepostal"]/@value')(self)
            cp = cp if cp else ''
            return u'%s %s (%s)' % (quartier, ville, cp)

        def obj_address(self):
            p = PostalAddress()

            p.street = Regexp(CleanText('//script'),
                              r"'nomQuartier', { value: \"([\w -]+)\", ")(self)
            p.postal_code = CleanText('//form[@name="central"]/input[@name="codepostal"]/@value')(self)
            p.city = CleanText('//form[@name="central"]/input[@name="ville"]/@value')(self)
            p.full_address = Field('location')(self)
            return p

        obj_text = CleanText('//form[@name="central"]/input[@name="description"]/@value')

        obj_cost = CleanDecimal(CleanText('//a[@id="price"]'), default=NotLoaded)
        obj_currency = Currency(CleanText('//a[@id="price"]'), default=NotLoaded)
        obj_price_per_meter = PricePerMeterFilter()

        obj_area = CleanDecimal('//form[@name="central"]/input[@name="surface"]/@value', replace_dots=True)
        obj_url = CleanText('//form[@name="central"]/input[@name="urlannonce"]/@value')
        obj_phone = CleanText('//div[@class="data-action"]/a[@data-phone]/@data-phone')

        def obj_utilities(self):
            mention = CleanText('//span[@class="detail_indice_prix"]', default="")(self)
            if "(CC) Loyer mensuel charges comprises" in mention:
                return UTILITIES.INCLUDED
            else:
                return UTILITIES.UNKNOWN

        def obj_bedrooms(self):
            return CleanDecimal(Dict('nb_chambres', default=NotLoaded))(self.house_json_datas)

        def obj_rooms(self):
            return CleanDecimal(Dict('nb_pieces', default=NotLoaded))(self.house_json_datas)


class HousingJsonPage(JsonPage):
    @method
    class get_housing(ItemElement):
        klass = Housing

        def obj_DPE(self):
            DPE = Dict("energie", default="")(self)
            if DPE['status'] > 0:
                return NotAvailable
            else:
                return getattr(ENERGY_CLASS, DPE['lettre'], NotAvailable)

        def obj_GES(self):
            GES = Dict("ges", default="")(self)
            if GES['status'] > 0:
                return NotAvailable
            else:
                return getattr(ENERGY_CLASS, GES['lettre'], NotAvailable)

        def obj_details(self):
            details = {}

            for c in Dict('categories')(self):
                if c['criteria']:
                    details[c['name']] = ' / '.join([_['value'] for _ in c['criteria']])

            for _, c in Dict('infos_acquereur')(self).items():
                for key, value in c.items():
                    details[key] = value

            return details

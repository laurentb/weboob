# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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

from lxml import objectify

from weboob.browser.pages import JsonPage, XMLPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env, Format, Filter, DateTime
from weboob.capabilities.housing import (Housing, HousingPhoto, City, UTILITIES, ENERGY_CLASS, ADVERT_TYPES)
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter
from weboob.capabilities.base import NotAvailable, Currency, empty

from .housing import RET, TYPES


class EPHouseType(Filter):
    def filter(self, _type):
        _type = str(_type)
        for key, value in RET.items():
            if _type == value:
                return key
        return NotAvailable


class EPAdvertType(Filter):
    def filter(self, _type):
        _type = str(_type)
        for key, value in TYPES.items():
            if _type == value:
                return key
        return NotAvailable


class SearchPage(JsonPage):
    @method
    class iter_houses(DictElement):
        class item(ItemElement):
            klass = Housing

            obj_id = Format("%s#%s", Dict('rubrique'), Dict('idannonce'))
            obj_type = EPAdvertType(Dict('rubrique'))
            obj_advert_type = ADVERT_TYPES.PERSONAL
            obj_house_type = EPHouseType(Dict('tbien'))
            obj_title = Dict('titre')
            obj_cost = CleanDecimal(Dict('prix'))
            obj_currency = Currency.get_currency(u'€')
            obj_text = Dict('titre')
            obj_location = Dict('ville')
            obj_area = CleanDecimal(Dict('surface'))
            obj_rooms = CleanDecimal(Dict('pieces'))
            obj_date = DateTime(Dict('creationdate'))
            obj_utilities = UTILITIES.UNKNOWN
            obj_price_per_meter = PricePerMeterFilter()

            def obj_photos(self):
                photos = []
                photo = Dict('UrlImage',
                             default=NotAvailable)(self)
                if not empty(photo):
                    photos.append(HousingPhoto(photo))
                return photos


class CitiesPage(JsonPage):

    @method
    class iter_cities(DictElement):
        class item(ItemElement):
            klass = City

            def condition(self):
                return Dict('localisationid', default=None)(self) and\
                    Dict('localisationType')(self) == 5

            obj_id = Dict('localisationid')
            obj_name = Dict('label')


class HousingPage(XMLPage):

    def build_doc(self, content):
        doc = super(HousingPage, self).build_doc(content).getroot()
        for elem in doc.getiterator():
            if not hasattr(elem.tag, 'find'):
                continue
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i+1:]
        objectify.deannotate(doc, cleanup_namespaces=True)
        return doc

    @method
    class get_housing(ItemElement):
        klass = Housing

        obj_id = Env('_id')
        obj_type = EPAdvertType(CleanText('//rubrique'))
        obj_advert_type = ADVERT_TYPES.PERSONAL
        obj_house_type = EPHouseType(CleanText('//tbien'))
        obj_title = CleanText('//titre')
        obj_rooms = CleanDecimal('//pieces')
        obj_cost = CleanDecimal('//prix')
        obj_currency = Currency.get_currency(u'€')
        obj_utilities = UTILITIES.UNKNOWN
        obj_text = CleanText('//titre')
        obj_location = CleanText('//ville')
        obj_url = CleanText('//urlDetailAnnonce')
        obj_area = CleanDecimal('//surface')
        obj_price_per_meter = PricePerMeterFilter()
        obj_phone = CleanText('//telephone1')
        obj_date = DateTime(CleanText('//DateCheck'))

        def obj_GES(self):
            value = CleanText('//GSE')(self)
            return getattr(ENERGY_CLASS, value.upper(), NotAvailable)

        def obj_photos(self):
            photos = []
            for photo in ['//UrlImage1', '//UrlImage2', '//UrlImage3']:
                p = CleanText(photo)(self)
                if p:
                    photos.append(HousingPhoto(p))
            return photos

        def obj_DPE(self):
            value = CleanText('//DPE')(self)
            return getattr(ENERGY_CLASS, value.upper(), NotAvailable)

        def obj_details(self):
            details = dict()
            d = [('//Nb_Etage', 'Nombre d\'etages'),
                 ('//Neuf', 'Neuf'),
                 ('//Ancien_avec_du_Charme', 'Ancien avec charme'),
                 ('//Avec_terasse', 'Avec Terrasse'),
                 ('//latitude', 'Latitude'),
                 ('//longitude', 'Longitude'),
                 ('//loyer', 'Loyer'),
                 ('//piscine', 'Piscine'),
                 ('//surface_balcon', 'Surface du balcon'),
                 ('//surface_exp', 'Surface exploitable'),
                 ('//surface_terrain', 'Surface du Terrain'),
                 ('//Meuble', 'furnished')]

            for key, value in d:
                key = CleanText(key)(self)
                if key:
                    details[value] = key

            return details

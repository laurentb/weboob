# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from weboob.browser.pages import XMLPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import XPath
from weboob.browser.filters.standard import CleanText, CleanDecimal, DateTime
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing, HousingPhoto, City


class CitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        item_xpath = '*/values'
        ignore_duplicate = True

        class item(ItemElement):
            klass = City

            def condition(self):
                return Dict('value', default=None)(self)

            obj_id = Dict('value')
            obj_name = Dict('label')


class SeLogerItem(ItemElement):
    klass = Housing

    obj_id = CleanText('idAnnonce')
    obj_title = CleanText('titre')
    obj_date = DateTime(CleanText('dtFraicheur'))
    obj_cost = CleanDecimal('prix')
    obj_currency = CleanText('prixUnite')
    obj_area = CleanDecimal('surface', default=NotAvailable)
    obj_text = CleanText('descriptif')
    obj_location = CleanText('ville')
    obj_station = CleanText('proximite', default=NotAvailable)
    obj_url = CleanText('permaLien')


class SearchResultsPage(XMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = "//annonce"

        def next_page(self):
            page = CleanText('//pageSuivante', default=None)(self)
            if page:
                return page

        class item(SeLogerItem):
            def obj_photos(self):
                photos = []

                for photo in XPath('./photos/photo/stdUrl')(self):
                    photos.append(HousingPhoto(CleanText('.')(photo)))

                return photos


class HousingPage(XMLPage):
    @method
    class get_housing(SeLogerItem):

        def obj_photos(self):
            photos = []

            for photo in XPath('./photos/photo')(self):
                url = CleanText('bigUrl', default=None)(photo)
                if not url:
                    url = CleanText('stdUrl', default=None)(photo)
                photos.append(HousingPhoto(url))
            return photos

        def obj_location(self):
            location = CleanText('//detailAnnonce/adresse')(self)
            quartier = CleanText('//detailAnnonce/quartier', default=None)(self)
            if not location and quartier is not None:
                location = quartier
            ville = CleanText('ville')(self)
            return u'%s %s' % (location, ville)

        def obj_details(self):
            details = {}
            for detail in XPath('//detailAnnonce/details/detail')(self):
                details[CleanText('libelle')(detail)] = CleanText('valeur', default='N/A')(detail)

            details['Reference'] = CleanText('//detailAnnonce/reference')(self)
            return details

        obj_phone = CleanText('//contact/telephone')

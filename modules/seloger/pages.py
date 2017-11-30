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
from weboob.browser.filters.standard import (CleanText, CleanDecimal, Currency,
                                             DateTime, Format, Regexp)
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import (Housing, HousingPhoto, City,
                                         UTILITIES, ENERGY_CLASS)
from weboob.tools.capabilities.housing.housing import PricePerMeterFilter

from .constants import TYPES, RET


class CitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        item_xpath = '*/values'
        ignore_duplicate = True

        class item(ItemElement):
            klass = City

            def condition(self):
                return (
                    Dict('value', default=None)(self) and
                    Dict('name', default=None)(self) == "ci"
                )

            obj_id = Dict('value')
            obj_name = Dict('label')


class SeLogerItem(ItemElement):
    klass = Housing

    obj_id = CleanText('idAnnonce')

    def obj_type(self):
        idType = int(CleanText('idTypeTransaction')(self))
        return next(k for k, v in TYPES.items() if v == idType)
    obj_advert_type = NotAvailable
    def obj_house_type(self):
        idType = CleanText('idTypeBien')(self)
        try:
            return next(k for k, v in RET.items() if v == idType)
        except StopIteration:
            return NotAvailable

    obj_title = Format(
        "%s %s%s - %s",
        CleanText('titre'),
        CleanText('surface'),
        CleanText('surfaceUnite'),
        CleanText('ville'),
    )
    obj_date = DateTime(CleanText('dtFraicheur'))
    obj_cost = CleanDecimal('prix')

    obj_currency = Currency('prixUnite')

    obj_area = CleanDecimal('surface', default=NotAvailable)
    obj_price_per_meter = PricePerMeterFilter()
    obj_text = CleanText('descriptif')
    obj_rooms = CleanDecimal('nbPiece|nbPieces', default=NotAvailable)
    obj_bedrooms = CleanDecimal('nbChambre|nbChambres', default=NotAvailable)

    def obj_location(self):
        location = CleanText('adresse', default="")(self)
        quartier = CleanText('quartier', default=None)(self)
        if not location and quartier is not None:
            location = quartier
        ville = CleanText('ville')(self)
        cp = CleanText('cp')(self)
        return u'%s %s (%s)' % (location, ville, cp)

    obj_station = CleanText('proximite', default=NotAvailable)
    obj_url = CleanText('permaLien')


class SearchResultsPage(XMLPage):
    @pagination
    @method
    class iter_housings(ListElement):
        item_xpath = "//annonce"

        def next_page(self):
            page = CleanText('//pageSuivante', default=None, replace=[('http://ws.seloger.com/', '')])(self)
            if page:
                return page

        class item(SeLogerItem):
            def obj_photos(self):
                photos = []

                for photo in XPath('./photos/photo/stdUrl')(self):
                    photos.append(HousingPhoto(CleanText('.')(photo)))

                return photos

            def obj_utilities(self):
                currency = CleanText('prixUnite')(self)
                if "+ch" in currency:
                    return UTILITIES.EXCLUDED
                elif "cc*" in currency:
                    return UTILITIES.INCLUDED
                else:
                    return UTILITIES.UNKNOWN


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

        def obj_DPE(self):
            DPE = CleanText('//bilanConsoEnergie', default="")(self)
            return getattr(ENERGY_CLASS, DPE, NotAvailable)

        def obj_GES(self):
            GES = CleanText('//bilanEmissionGES', default="")(self)
            return getattr(ENERGY_CLASS, GES, NotAvailable)

        def obj_details(self):
            details = {}
            for detail in XPath('//detailAnnonce/details/detail')(self):
                details[CleanText('libelle')(detail)] = CleanText('valeur', default='N/A')(detail)

            details['Reference'] = CleanText('//detailAnnonce/reference')(self)
            return details

        obj_phone = CleanText('//contact/telephone')

        def obj_utilities(self):
            mention = CleanText('prixMention')(self)
            if "charges comprises" in mention:
                return UTILITIES.INCLUDED
            else:
                return UTILITIES.UNKNOWN

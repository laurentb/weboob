# -*- coding: utf-8 -*-

# Copyright(C) 2018 Quentin Defenouillere
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals


from weboob.browser.pages import JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    Regexp, CleanText, Format, Env,
)
from weboob.browser.filters.html import Link
from weboob.capabilities.bands import Bandinfo, Bandsearch, Favorites, Albums, Suggestions


class LoginPage(HTMLPage):
    """
    Login to your Metal Archives account.
    """
    @property
    def logged(self):
        return self.doc['Success']


class SearchBandsPage(JsonPage):
    @method
    class iter_bands(DictElement):
        item_xpath = 'aaData'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Bandsearch
            obj_id = Regexp(Dict('0'), '/([0-9]+)\\"')
            obj_name = Regexp(Dict('0'), '>([^<]+)')
            obj_short_description = Format('Genre: %s - Country: %s', Dict('1'), Dict('2'))


class BandPage(HTMLPage):
    """
    Displays information about a band.
    """
    @method
    class get_info(ItemElement):
        klass = Bandinfo

        obj_id = Env('band_id')
        obj_name = CleanText('//h1[@class="band_name"]/a/text()')
        obj_genre = CleanText('//dl[@class="float_right"]/dd[1]/text()')
        obj_country = CleanText('//dl[@class="float_left"]/dd[1]/a/text()')
        obj_year = CleanText('//dl[@class="float_left"]/dd[4]/text()')
        obj_description = CleanText('//div[@class="band_comment clear"]/text()')


class AlbumPage(HTMLPage):
    """
    Displays a band's discography.
    """
    @method
    class iter_albums(ListElement):
        item_xpath = '//tbody/tr'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Albums

            obj_id = Link('./td[1]/a')
            obj_name = CleanText('./td[1]/a/text()')
            obj_album_type = CleanText('./td[2]/text()')
            obj_year = CleanText('./td[3]/text()')
            obj_reviews = CleanText('./td[4]/a/text()')


class FavoritesPage(JsonPage):
    """
    Display a list of your favorite bands.
    """
    @method
    class iter_favorites(DictElement):
        item_xpath = 'aaData'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Favorites

            obj_id = Regexp(Dict('0'), '/([0-9]+)\\"')
            obj_name = Regexp(Dict('0'), '>([^<]+)')
            obj_band_url = Regexp(Dict('0'), 'href=\"([^"]+)')
            obj_short_description = Format('Genre: %s - Country: %s', Dict('2'), Dict('1'))


class SuggestionsPage(HTMLPage):
    """
    Displays band suggestions depending on your favorite bands.
    """
    @method
    class iter_suggestions(ListElement):
        # Takes all the <td> except the last one that is not a band
        item_xpath = '//tbody/tr[position() < last()]'
        class item(ItemElement):
            klass = Suggestions

            obj_id = Regexp(Link('./td[2]/a'), '/([0-9]+)')
            obj_name = CleanText('./td[2]/a/text()')
            obj_description = Format('Genre: %s - Country: %s', CleanText('./td[3]/text()'), CleanText('./td[4]/text()'))
            obj_url = Link('./td[2]/a')

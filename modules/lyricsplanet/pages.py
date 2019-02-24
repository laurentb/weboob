# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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


from weboob.capabilities.lyrics import SongLyrics
from weboob.capabilities.base import NotLoaded, NotAvailable

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import Regexp, CleanText
from weboob.browser.filters.html import CleanHTML


class HomePage(HTMLPage):
    def search_lyrics(self, criteria, pattern):
        form = self.get_form(xpath='//form[@class="form-inline"]')
        form['value'] = pattern
        form['field'] = criteria.replace('song','title')
        form.submit()


class SearchPage(HTMLPage):
    @method
    class iter_song_lyrics(ListElement):
        item_xpath = '//div[@id="search"]//div[has-class("row")]//td/a'

        class item(ItemElement):
            klass = SongLyrics

            obj_id = Regexp(CleanText('./@href', default=NotAvailable), 'id=(.*)$')
            obj_title = Regexp(CleanText('.', default=NotAvailable), '(.*) - .*')
            obj_artist = Regexp(CleanText('.', default=NotAvailable), '.* - (.*)')
            obj_content = NotLoaded

    def get_artist_ids(self):
        artists_href = self.doc.xpath('//div[@id="search"]//div[has-class("row")]//td/a/@href')
        aids = [href.split('value=')[-1] for href in artists_href]
        return aids


class ArtistPage(HTMLPage):
    @method
    class iter_lyrics(ListElement):
        item_xpath = '//div[@id="search"]//div[has-class("row")]//td/a'

        class item(ItemElement):
            klass = SongLyrics

            obj_id = Regexp(CleanText('./@href', default=NotAvailable), 'id=(.*)$')
            obj_artist = Regexp(CleanText('.', default=NotAvailable), '(.*) - .*')
            obj_title = Regexp(CleanText('.', default=NotAvailable), '.* - (.*)')
            obj_content = NotLoaded


class LyricsPage(HTMLPage):
    @method
    class get_lyrics(ItemElement):
        klass = SongLyrics

        def obj_id(self):
            return self.page.url.split('id=')[-1]
        obj_content = CleanText(CleanHTML('//div[has-class("btn-toolbar")]/following-sibling::div[2]',
                                          default=NotAvailable),
                                newlines=False)
        obj_artist = Regexp(CleanText('//title', default=NotAvailable), '(.*) - .* - .*')
        obj_title = Regexp(CleanText('//title', default=NotAvailable), '.* - (.*) - .*')


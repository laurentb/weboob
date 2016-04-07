# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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


from weboob.capabilities.lyrics import SongLyrics
from weboob.capabilities.base import NotLoaded, NotAvailable

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import Regexp, CleanText
from weboob.browser.filters.html import CleanHTML


class SearchPage(HTMLPage):
    @method
    class iter_lyrics(ListElement):
        item_xpath = '//div[has-class("row")]'

        class item(ItemElement):
            klass = SongLyrics

            def obj_id(self):
                real_id = Regexp(CleanText('.//a[has-class("lyrics_preview")]/@href', default=NotAvailable),
                    '/(.*)\.html')(self)
                # to avoid several times the same ID (damn website)
                salt_id = Regexp(CleanText('.//a[has-class("lyrics_preview")]/@t_id', default=NotAvailable),
                    'T (.*)')(self)
                return '%s|%s' % (real_id, salt_id)
            obj_title = CleanText('.//a[has-class("lyrics_preview")]', default=NotAvailable)
            obj_artist = CleanText('.//a[has-class("artist_link")]', default=NotAvailable)
            obj_content = NotLoaded


class LyricsPage(HTMLPage):
    @method
    class get_lyrics(ItemElement):
        klass = SongLyrics

        def obj_id(self):
            subid = self.page.url.replace('.html','').split('/')[-1].replace('/','')
            # sorry for the potential id comparison mistakes in application level. you know what i mean ?
            id = '%s|000' % (subid)
            return id
        obj_content = CleanText(CleanHTML('//div[@id="lyrics"]', default=NotAvailable), newlines=False)
        def obj_title(self):
            artist = CleanText('//h1[@id="profile_name"]//a', default=NotAvailable)(self)
            fullhead = CleanText('//h1[@id="profile_name"]', default=NotAvailable)(self)
            return fullhead.replace('by %s' % artist, '')
        obj_artist = CleanText('//h1[@id="profile_name"]//a', default=NotAvailable)

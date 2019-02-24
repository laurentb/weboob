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
from weboob.capabilities.base import NotLoaded, NotAvailable, BaseObject

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import Regexp, CleanText, Env, BrowserURL
from weboob.browser.filters.html import CleanHTML, XPath


class SearchPage(HTMLPage):
    @method
    class iter_lyrics(ListElement):
        item_xpath = '//div[has-class("sec-lyric")]'

        class item(ItemElement):
            klass = SongLyrics

            def condition(self):
                title = CleanText('./div/p[@class="lyric-meta-title"]/a', default="")(self)
                content = CleanText('./pre[@class="lyric-body"]')(self)
                return content.replace(title, "").strip() != ""

            obj_id = Regexp(CleanText('./div/p[@class="lyric-meta-title"]/a/@href', default=NotAvailable),
                            '/lyric/(.*)')

            obj_title = CleanText('./div/p[@class="lyric-meta-title"]/a', default=NotAvailable)

            obj_artist = CleanText('./div/p[@class="lyric-meta-artists"]/a', default=NotAvailable)

            obj_content = NotLoaded

    @method
    class iter_artists(ListElement):
        item_xpath = '//td[@class="tal qx"]'

        class item(ItemElement):
            klass = BaseObject

            def condition(self):
                return CleanText('.//a/@href')(self)

            obj_id = Regexp(CleanText('.//a/@href'), 'artist/(.*)')


class LyricsPage(HTMLPage):
    @method
    class get_lyrics(ItemElement):
        klass = SongLyrics

        def condition(self):
            return not XPath('//div[has-class("lyric-no-data")]')(self)

        obj_id = Env('id')
        obj_url = BrowserURL('songLyrics', id=Env('id'))
        obj_content = CleanHTML('//pre[@id="lyric-body-text"]', default=NotAvailable)
        obj_title = CleanText('//h2[@id="lyric-title-text"]')
        obj_artist = CleanText('//h3[@class="lyric-artist"]/a[1]', default=NotAvailable)


class ArtistPages(HTMLPage):
    @method
    class iter_lyrics(ListElement):
        item_xpath = '//td[@class="tal qx"]'

        class item(ItemElement):
            klass = SongLyrics

            def condition(self):
                return CleanText('./strong/a/@href')(self)

            obj_id = Regexp(CleanText('./strong/a/@href'), '/lyric/(.*)')
            obj_title = CleanText('./strong/a', default=NotAvailable)
            obj_artist = CleanText('//h3/strong', default=NotAvailable)
            obj_content = NotLoaded

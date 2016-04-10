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
        item_xpath = '//table[has-class("songs_list")]//tr[count(td) = 2]'

        class item(ItemElement):
            klass = SongLyrics

            obj_id = CleanText('./@href', default=NotAvailable)
            def obj_id(self):
                href = CleanText('./td[2]/a/@href', default=NotAvailable)(self)
                spl = href.replace('.html', '').split('/')
                lid = spl[2]
                aid = spl[3]
                sid = spl[4]
                return '%s|%s|%s' % (lid, aid, sid)
            obj_title = Regexp(CleanText('./td[2]', default=NotAvailable), '(.*) lyrics$')
            obj_artist = CleanText('./td[1]/a', default=NotAvailable)
            obj_content = NotLoaded


class LyricsPage(HTMLPage):
    @method
    class get_lyrics(ItemElement):
        klass = SongLyrics

        def obj_id(self):
            spl = self.page.url.replace('http://', '').replace('.html', '').split('/')
            lid = spl[2]
            aid = spl[3]
            sid = spl[4]
            return '%s|%s|%s' % (lid, aid, sid)
        obj_content = CleanText(CleanHTML('//p[@id="lyrics_text"]', default=NotAvailable), newlines=False)
        obj_artist = CleanText('//a[has-class("header-band-name")]', default=NotAvailable)
        obj_title = Regexp(CleanText('//h1[has-class("header-song-name")]', default=NotAvailable), '(.*) lyrics$')

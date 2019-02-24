# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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
    def search_lyrics(self, pattern):
        form = self.get_form(xpath='//form[@id="search-form-round"]')
        form['search'] = pattern
        form.submit()


class ResultsPage(HTMLPage):
    @method
    class iter_song_lyrics(ListElement):
        item_xpath = '//h2[text()="Chansons"]/following-sibling::div[position() <= 2]//tr'

        class item(ItemElement):
            klass = SongLyrics

            def obj_id(self):
                href = CleanText('.//td[has-class("song-name")]//a/@href')(self)
                aid = href.split('/')[-2]
                sid = href.split('/')[-1].replace('paroles-','')
                id = '%s|%s'%(aid, sid)
                return id

            obj_title = CleanText('.//td[has-class("song-name")]',
                    default=NotAvailable)
            obj_artist = CleanText('.//td[has-class("song-artist")]',
                    default=NotAvailable)
            obj_content = NotLoaded

    def get_artist_ids(self):
        artists_href = self.doc.xpath('//h2[text()="Artiste"]/following-sibling::div[position() <= 2]//tr//a/@href')
        aids = [href.split('/')[-1] for href in artists_href]
        return aids


class ArtistSongsPage(HTMLPage):
    @method
    class iter_lyrics(ListElement):
        item_xpath = '//div[@id="main"]//div[has-class("song-listing-extra")]//td[has-class("song-name")]//a'

        class item(ItemElement):
            klass = SongLyrics

            obj_title = CleanText('.',
                    default=NotAvailable)
            obj_artist = Regexp(CleanText('//div[has-class("breadcrumb")]//span[has-class("breadcrumb-current")]'),
                    'Paroles (.*)')
            obj_content = NotLoaded
            def obj_id(self):
                href = CleanText('./@href')(self)
                aid = href.split('/')[-2]
                sid = href.split('/')[-1].replace('paroles-','')
                id = '%s|%s'%(aid, sid)
                return id


class SongLyricsPage(HTMLPage):
    @method
    class get_lyrics(ItemElement):
        klass = SongLyrics

        def obj_id(self):
            subid = self.page.url.replace('paroles-','').split('/')[-2:]
            id = '%s|%s'%(subid[0], subid[1])
            return id
        obj_content = CleanText(CleanHTML('//div[has-class("song-text")]', default=NotAvailable), newlines=False)
        obj_title = CleanText('//span[@property="v:name"]', default=NotAvailable)
        obj_artist = CleanText('//span[@property="v:artist"]', default=NotAvailable)


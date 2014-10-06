# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.deprecated.browser import Page


class HomePage(Page):
    def iter_lyrics(self, criteria, pattern):
        self.browser.select_form(name='rechercher')
        if criteria == 'artist':
            self.browser['termes_a'] = pattern
        else:
            self.browser['termes_t'] = pattern
        self.browser.submit()
        assert self.browser.is_on_page(SongResultsPage) or self.browser.is_on_page(ArtistResultsPage)
        for lyr in self.browser.page.iter_lyrics():
            yield lyr


class ArtistResultsPage(Page):
    def iter_lyrics(self):
        for link in self.parser.select(self.document.getroot(), 'div.cont_cat table a.std'):
            artist = unicode(link.text_content())
            self.browser.location('http://www.paroles-musique.com%s' % link.attrib.get('href', ''))
            assert self.browser.is_on_page(ArtistSongsPage)
            for lyr in self.browser.page.iter_lyrics(artist):
                yield lyr


class ArtistSongsPage(Page):
    def iter_lyrics(self, artist):
        for link in self.parser.select(self.document.getroot(), 'div.cont_catA div.art_scroll a'):
            href = link.attrib.get('href', '')
            if href.startswith('./paroles'):
                title = unicode(link.text)
                id = href.replace('./paroles-', '')
                songlyrics = SongLyrics(id, title)
                songlyrics.artist = artist
                songlyrics.content = NotLoaded
                yield songlyrics


class SongResultsPage(Page):
    def iter_lyrics(self):
        first = True
        for tr in self.parser.select(self.document.getroot(), 'div.cont_cat table tr'):
            if first:
                first = False
                continue
            artist = NotAvailable
            links = self.parser.select(tr, 'a.std')
            title = unicode(links[0].text)
            id = links[0].attrib.get('href', '').replace('/paroles-', '')
            artist = unicode(links[1].text)
            songlyrics = SongLyrics(id, title)
            songlyrics.artist = artist
            songlyrics.content = NotLoaded
            yield songlyrics


class SonglyricsPage(Page):
    def get_lyrics(self, id):
        artist = NotAvailable
        title = NotAvailable
        content = unicode(self.parser.select(self.document.getroot(), 'div#lyr_scroll', 1).text_content().strip())
        infos = self.parser.select(self.document.getroot(), 'h2.lyrics > font')
        artist = unicode(infos[0].text)
        title = unicode(infos[1].text)
        songlyrics = SongLyrics(id, title)
        songlyrics.artist = artist
        songlyrics.content = content
        return songlyrics

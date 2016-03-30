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


class ArtistResultsPage(Page):
    def iter_lyrics(self):
        for link in self.parser.select(self.document.getroot(), 'div.elenco div li a'):
            artist = unicode(link.text_content())
            href = link.attrib.get('href', '')
            if href.startswith('/paroles'):
                self.browser.location('http://www.parolesmania.com%s' % href)
                assert self.browser.is_on_page(ArtistSongsPage)
                for lyr in self.browser.page.iter_lyrics(artist):
                    yield lyr


class ArtistSongsPage(Page):
    def iter_lyrics(self, artist=None):
        if artist is None:
            artist = self.parser.select(self.document.getroot(), 'head > title', 1).text.replace('Paroles ', '')
        for link in self.parser.select(self.document.getroot(), 'div.album ul li a'):
            href = link.attrib.get('href', '')
            titleattrib = link.attrib.get('title', '')
            if href.startswith('/paroles') and not href.endswith('alpha.html') and titleattrib.startswith('Paroles '):
                title = unicode(link.text)
                ids = href.replace('/', '').replace('.html', '').split('paroles_')
                id = '%s|%s' % (ids[1], ids[2])
                songlyrics = SongLyrics(id)
                songlyrics.artist = artist
                songlyrics.title = title
                songlyrics.id = id
                songlyrics.content = NotLoaded
                yield songlyrics


class SongResultsPage(Page):
    def iter_lyrics(self):
        for link in self.parser.select(self.document.getroot(), 'div.elenco div.col-left li a'):
            artist = NotAvailable
            title = unicode(link.text.split(' - ')[0])
            href = link.attrib.get('href', '')
            if href.startswith('/paroles') and not href.endswith('alpha.html'):
                ids = href.replace('/', '').replace('.html', '').split('paroles_')
                id = '%s|%s' % (ids[1], ids[2])
                artist = unicode(link.text.split(' - ')[1])
                songlyrics = SongLyrics(id, title)
                songlyrics.artist = artist
                songlyrics.content = NotLoaded
                songlyrics.title = title
                songlyrics.id = id
                yield songlyrics


class SonglyricsPage(Page):
    def get_lyrics(self, id):
        content = NotAvailable
        artist = NotAvailable
        title = NotAvailable
        lyrdiv = self.parser.select(self.document.getroot(), 'div.lyrics-body')
        if len(lyrdiv) > 0:
            content = unicode(lyrdiv[0].text_content().strip())
        infos = self.parser.select(self.document.getroot(), 'head > title', 1).text
        artist = unicode(infos.split(' - ')[1])
        title = unicode(infos.split(' - ')[0].replace('Paroles ', ''))
        songlyrics = SongLyrics(id, title)
        songlyrics.artist = artist
        songlyrics.content = content
        return songlyrics

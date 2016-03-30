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
        self.browser.select_form(nr=0)
        self.browser['search'] = pattern
        self.browser.submit()
        assert self.browser.is_on_page(ResultsPage)
        for lyr in self.browser.page.iter_lyrics(criteria):
            yield lyr


class ResultsPage(Page):
    def iter_lyrics(self, criteria):
        for link in self.parser.select(self.document.getroot(), 'div.box-content td.song-name a'):
            href = link.attrib.get('href','')
            if criteria == 'artist':
                if len(href.split('/')) != 4:
                    continue
                else:
                    self.browser.location('%s' % href)
                    assert self.browser.is_on_page(ArtistSongsPage) or self.browser.is_on_page(SonglyricsPage)
                    for lyr in self.browser.page.iter_lyrics():
                        yield lyr
            else:
                if len(href.split('/')) != 5:
                    continue
                else:
                    artist = unicode(self.parser.select(link.getparent().getparent().getparent(), 'td.song-artist > p', 1).text.strip())
                    title = unicode(link.text)
                    id = unicode(link.attrib.get('href', '').replace('http://www.paroles.net/',''))
                    lyr = SongLyrics(id)
                    lyr.title = title
                    lyr.artist = artist
                    yield lyr


class ArtistSongsPage(Page):
    def iter_lyrics(self):
        artist = unicode(self.parser.select(self.document.getroot(), 'span[itemprop=name]', 1).text)
        for link in self.parser.select(self.document.getroot(), 'td.song-name > p[itemprop=name] > a[itemprop=url]'):
            href = unicode(link.attrib.get('href', ''))
            title = unicode(link.text)
            id = href.replace('http://www.paroles.net/', '')
            songlyrics = SongLyrics(id)
            songlyrics.artist = artist
            songlyrics.title = title
            songlyrics.content = NotLoaded
            yield songlyrics


class SonglyricsPage(Page):
    def get_lyrics(self, id):
        artist = NotAvailable
        title = NotAvailable
        content = unicode(self.parser.select(self.document.getroot(), 'div.song-text', 1).text_content().strip())
        artist = unicode(self.parser.select(self.document.getroot(), 'span[property$=artist]', 1).text)
        title = unicode(self.parser.select(self.document.getroot(), 'span[property$=name]', 1).text)
        songlyrics = SongLyrics(id)
        songlyrics.artist = artist
        songlyrics.title = title
        songlyrics.content = content
        return songlyrics

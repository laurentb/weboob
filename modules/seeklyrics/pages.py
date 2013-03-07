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


try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs  # NOQA

from urlparse import urlsplit

from weboob.capabilities.lyrics import SongLyrics
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.browser import BasePage


__all__ = ['ResultsPage','SonglyricsPage']


class ResultsPage(BasePage):
    def iter_lyrics(self):
        first = True
        for tr in self.parser.select(self.document.getroot(),'table[title~=Results] tr'):
            if first:
                first = False
                continue
            artist = NotAvailable
            ftitle = self.parser.select(tr,'a > font > font',1)
            title = ftitle.getparent().getparent().text_content()
            id = ftitle.getparent().getparent().attrib.get('href','').replace('/lyrics/','').replace('.html','')
            aartist = self.parser.select(tr,'a')[-1]
            artist = aartist.text
            songlyrics = SongLyrics(id, title)
            songlyrics.artist = artist
            songlyrics.content = NotLoaded
            yield songlyrics


class SonglyricsPage(BasePage):
    def get_lyrics(self, id):
        artist = NotAvailable
        title = NotAvailable
        l_artitle = self.parser.select(self.document.getroot(),'table.text td > b > h2')
        if len(l_artitle) > 0:
            artitle = l_artitle[0].text.split(' Lyrics by ')
            artist = artitle[1]
            title = artitle[0]
        content = self.parser.select(self.document.getroot(),'div#songlyrics',1).text_content().strip()
        songlyrics = SongLyrics(id, title)
        songlyrics.artist = artist
        songlyrics.content = content
        return songlyrics

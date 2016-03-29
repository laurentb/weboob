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


from weboob.browser.exceptions import BrowserHTTPNotFound
from weboob.browser import PagesBrowser
from weboob.browser.url import URL
from weboob.browser.profiles import Firefox

from .pages import SearchPage, LyricsPage, HomePage, ArtistPage


__all__ = ['Paroles2chansonsBrowser']


class Paroles2chansonsBrowser(PagesBrowser):
    PROFILE = Firefox()
    TIMEOUT = 30

    BASEURL = 'http://www.paroles2chansons.com/'
    home = URL('$',
                 HomePage)
    search = URL('search',
                 SearchPage)
    artist = URL('paroles-(?P<artistid>[^/]*)$',
                  ArtistPage)
    lyrics = URL('paroles-(?P<artistid>[^/]*)/paroles-(?P<songid>[^/]*)\.html',
                  LyricsPage)

    def iter_lyrics(self, criteria, pattern):
        self.home.stay_or_go()
        assert self.home.is_here()
        self.page.search_lyrics(pattern)
        assert self.search.is_here()
        if criteria == 'song':
            return self.page.iter_song_lyrics()
        else:
            return self.page.iter_artist_lyrics()

    def get_lyrics(self, id):
        ids = id.split('|')
        try:
            self.lyrics.go(artistid=ids[0], songid=ids[1])
            songlyrics = self.page.get_lyrics()
            return songlyrics
        except BrowserHTTPNotFound:
            return

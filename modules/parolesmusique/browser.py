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

from .pages import SongResultsPage, SonglyricsPage, ArtistResultsPage, ArtistSongsPage, HomePage

import itertools


__all__ = ['ParolesmusiqueBrowser']


class ParolesmusiqueBrowser(PagesBrowser):
    PROFILE = Firefox()
    TIMEOUT = 30

    BASEURL = 'http://www.paroles-musique.com/'
    home = URL('$',
                 HomePage)
    songResults = URL('lyrics-paroles-0-.*,0.php',
                 SongResultsPage)
    artistResults = URL('lyrics-paroles-.*-0,0.php',
                  ArtistResultsPage)
    songLyrics = URL('paroles-(?P<songid>.*,p[0-9]*)',
                  SonglyricsPage)
    artistSongs = URL('paroles-(?P<artistid>.*,a[0-9]*)',
                  ArtistSongsPage)


    def iter_lyrics(self, criteria, pattern):
        self.home.stay_or_go()
        assert self.home.is_here()
        self.page.search_lyrics(criteria, pattern)
        if criteria == 'song':
            assert self.songResults.is_here()
            return self.page.iter_lyrics()
        elif criteria == 'artist':
            assert self.artistResults.is_here()
            artist_ids = self.page.get_artist_ids()
            it = []
            # we just take the 3 first artists to avoid too many page loadings
            for aid in artist_ids[:3]:
                it = itertools.chain(it, self.artistSongs.go(artistid=aid).iter_lyrics())
            return it


    def get_lyrics(self, id):
        try:
            self.songLyrics.go(songid=id)
            songlyrics = self.page.get_lyrics()
            return songlyrics
        except BrowserHTTPNotFound:
            return


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


from weboob.browser.exceptions import BrowserHTTPNotFound
from weboob.browser import PagesBrowser
from weboob.browser.url import URL
from weboob.browser.profiles import Firefox

from .pages import SearchSongPage, LyricsPage, SearchArtistPage, ArtistSongsPage

import itertools


__all__ = ['ParolesmaniaBrowser']


class ParolesmaniaBrowser(PagesBrowser):
    PROFILE = Firefox()
    TIMEOUT = 30

    BASEURL = 'http://www.parolesmania.com/'
    searchSong = URL('recherche.php\?c=title&k=(?P<pattern>[^/]*).*',
                 SearchSongPage)
    searchArtist = URL('recherche.php\?c=artist&k=(?P<pattern>[^/]*).*',
                  SearchArtistPage)
    songLyrics = URL('paroles_(?P<artistid>[^/]*)/paroles_(?P<songid>[^/]*)\.html',
                  LyricsPage)
    artistSongs = URL('paroles_(?P<artistid>[^/]*)\.html',
                  ArtistSongsPage)


    def iter_lyrics(self, criteria, pattern):
        if criteria == 'artist':
            artist_ids = self.searchArtist.go(pattern=pattern).get_artist_ids()
            it = []
            # we just take the 3 first artists to avoid too many page loadings
            for aid in artist_ids[:3]:
                it = itertools.chain(it, self.artistSongs.go(artistid=aid).iter_lyrics())
            return it
        elif criteria == 'song':
            return self.searchSong.go(pattern=pattern).iter_lyrics()

    def get_lyrics(self, id):
        ids = id.split('|')
        try:
            self.songLyrics.go(artistid=ids[0], songid=ids[1])
            songlyrics = self.page.get_lyrics()
            return songlyrics
        except BrowserHTTPNotFound:
            return


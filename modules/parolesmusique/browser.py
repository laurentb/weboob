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


from weboob.deprecated.browser import Browser, BrowserHTTPNotFound

from .pages import SongResultsPage, SonglyricsPage, ArtistResultsPage, ArtistSongsPage, HomePage


__all__ = ['ParolesmusiqueBrowser']


class ParolesmusiqueBrowser(Browser):
    DOMAIN = 'www.paroles-musique.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.paroles-musique.com': HomePage,
        'http://www.paroles-musique.com/lyrics-paroles-0-.*,0.php': SongResultsPage,
        'http://www.paroles-musique.com/lyrics-paroles-.*-0,0.php': ArtistResultsPage,
        'http://www.paroles-musique.com/paroles-.*p[0-9]*': SonglyricsPage,
        'http://www.paroles-musique.com/paroles-.*-lyrics,a[0-9]*': ArtistSongsPage,
    }

    def iter_lyrics(self, criteria, pattern):
        self.location('http://www.paroles-musique.com')
        assert self.is_on_page(HomePage)
        return self.page.iter_lyrics(criteria, pattern)

    def get_lyrics(self, id):
        try:
            self.location('http://www.paroles-musique.com/paroles-%s' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SonglyricsPage):
            return self.page.get_lyrics(id)

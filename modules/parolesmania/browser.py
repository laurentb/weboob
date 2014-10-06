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

from .pages import SongResultsPage, SonglyricsPage, ArtistResultsPage, ArtistSongsPage


__all__ = ['ParolesmaniaBrowser']


class ParolesmaniaBrowser(Browser):
    DOMAIN = 'www.parolesmania.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.parolesmania.com/recherche.php\?c=title.*': SongResultsPage,
        'http://www.parolesmania.com/recherche.php\?c=artist.*': ArtistResultsPage,
        'http://www.parolesmania.com/paroles.*[0-9]*/paroles.*': SonglyricsPage,
        'http://www.parolesmania.com/paroles[^/]*.html': ArtistSongsPage,
    }

    def iter_lyrics(self, criteria, pattern):
        crit = 'artist'
        if criteria != 'artist':
            crit = 'title'
        self.location('http://www.parolesmania.com/recherche.php?c=%s&k=%s' % (crit, pattern))
        assert self.is_on_page(SongResultsPage) or self.is_on_page(ArtistResultsPage)\
            or self.is_on_page(ArtistSongsPage)
        for lyr in self.page.iter_lyrics():
            yield lyr

    def get_lyrics(self, id):
        ids = id.split('|')
        try:
            self.location('http://www.parolesmania.com/paroles_%s/paroles_%s.html' % (ids[0], ids[1]))
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SonglyricsPage):
            return self.page.get_lyrics(id)

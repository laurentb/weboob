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


__all__ = ['SeeklyricsBrowser']


class SeeklyricsBrowser(Browser):
    DOMAIN = 'www.seeklyrics.com'
    PROTOCOL = 'http'
    ENCODING = 'iso-8859-1'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.seeklyrics.com/search.php.*t=1': SongResultsPage,
        'http://www.seeklyrics.com/search.php.*t=2': ArtistResultsPage,
        'http://www.seeklyrics.com/lyrics/.*html': SonglyricsPage,
        'http://www.seeklyrics.com/lyrics/.*/': ArtistSongsPage,
    }

    def iter_lyrics(self, criteria, pattern):
        if criteria == 'artist':
            type = 2
        else:
            type = 1
        self.location('http://www.seeklyrics.com/search.php?q=%s&t=%s' % (pattern, type))
        assert self.is_on_page(ArtistResultsPage) or self.is_on_page(SongResultsPage)
        return self.page.iter_lyrics()

    def get_lyrics(self, id):
        try:
            self.location('http://www.seeklyrics.com/lyrics/%s.html' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SonglyricsPage):
            return self.page.get_lyrics(id)

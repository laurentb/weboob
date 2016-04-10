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

from .pages import SearchPage, LyricsPage


__all__ = ['LyricsdotcomBrowser']


class LyricsdotcomBrowser(PagesBrowser):
    PROFILE = Firefox()
    TIMEOUT = 30

    BASEURL = 'http://www.lyrics.com/'
    search = URL('search\.php\?keyword=(?P<pattern>[^&]*)&what=all&search_btn=Search',
                 SearchPage)
    songLyrics = URL('(?P<id>[^/]*-lyrics-[^/]*)\.html$',
                  LyricsPage)


    def iter_lyrics(self, criteria, pattern):
        self.search.go(pattern=pattern)
        assert self.search.is_here()
        return self.page.iter_lyrics()

    def get_lyrics(self, id):
        real_id = id.split('|')[0]
        try:
            self.songLyrics.go(id=real_id)
            songlyrics = self.page.get_lyrics()
            return songlyrics
        except BrowserHTTPNotFound:
            return


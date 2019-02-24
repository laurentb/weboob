# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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

from .pages import SearchPage, TorrentPage#, HomePage


__all__ = ['CpasbienBrowser']


class CpasbienBrowser(PagesBrowser):
    PROFILE = Firefox()
    TIMEOUT = 30

    BASEURL = 'http://www.cpasbien.cm/'
    search = URL('recherche/(?P<pattern>.*).html,trie-seeds-d',
                 SearchPage)
    torrent = URL('dl-torrent/(?P<id>.*)\.html',
                  TorrentPage)

    def iter_torrents(self, pattern):
        self.search.go(pattern=pattern)
        return self.page.iter_torrents()

    def get_torrent(self, fullid):
        try:
            self.torrent.go(id=fullid)
            torrent = self.page.get_torrent()
            return torrent
        except BrowserHTTPNotFound:
            return

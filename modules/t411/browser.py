# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
# Copyright(C) 2016-2017 David Kremer
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
from weboob.browser import LoginBrowser, need_login
from weboob.browser.url import URL
from weboob.browser.profiles import Wget
from weboob.exceptions import BrowserIncorrectPassword

from .pages.index import HomePage, LoginPage
from .pages.torrents import TorrentPage, SearchPage, DownloadPage


__all__ = ['T411Browser']


class T411Browser(LoginBrowser):
    PROFILE = Wget()
    TIMEOUT = 30

    BASEURL = 'https://www.t411.si/'
    home = URL('$', HomePage)
    login = URL('/login$', LoginPage)
    search = URL(r'/torrents/search/\?search=(?P<pattern>.*)', SearchPage)
    download = URL('/telecharger-torrent/(?P<torrent_hash>[0-9a-f]{40})/(?P<torrent_name>\w+)', DownloadPage)
    torrent = URL('/torrents/(?P<torrent_id>[0-9]+)/(?P<torrent_name>.*)', TorrentPage)

    def do_login(self):
        self.home.go()
        if not self.page.logged:
            self.page.login(self.username, self.password)
            self.home.go()

        if not self.page.logged:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_torrents(self, pattern):
        return self.search.go(pattern=pattern).iter_torrents()

    @need_login
    def get_torrent(self, torrent):
        try:
            self.torrent.go(torrent_id=torrent.id, torrent_name=torrent.name)
            torrent = self.page.get_torrent()
            return torrent
        except BrowserHTTPNotFound:
            return

    def get_torrent_file(self, torrent):
        torrent = self.browser.get_torrent(torrent)
        if not torrent:
            return None
        resp = self.browser.open(torrent.url)
        return resp.content

# -*- coding: utf-8 -*-

# Copyright(C) 2018 Julien Veyssier
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
from weboob.browser import LoginBrowser, need_login
from weboob.browser.url import URL
from weboob.browser.profiles import Wget
from weboob.exceptions import BrowserIncorrectPassword

from .pages.index import HomePage, LoginPage
from .pages.torrents import TorrentPage, SearchPage, DownloadPage


__all__ = ['YggtorrentBrowser']


class YggtorrentBrowser(LoginBrowser):
    PROFILE = Wget()
    TIMEOUT = 30

    BASEURL = 'https://yggtorrent.to/'
    home = URL('$', HomePage)
    login = URL('/user/login$', LoginPage)
    search = URL(r'/engine/search\?name=(?P<pattern>.*)&order=desc&sort=seed&do=search', SearchPage)
    download = URL('/engine/download_torrent\?id=(?P<torrent_id>[0-9]+)', DownloadPage)
    torrent = URL('/torrent/(?P<torrent_cat>.+)/(?P<torrent_subcat>.+)/(?P<torrent_id>[0-9]+)-(?P<torrent_name>.*)', TorrentPage)

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
    def get_torrent(self, id):
        try:
            self.torrent.go(torrent_id=id, torrent_name='anything', torrent_cat='any', torrent_subcat='thing')
            torrent = self.page.get_torrent()
            return torrent
        except BrowserHTTPNotFound:
            return

    @need_login
    def get_torrent_file(self, id):
        torrent = self.browser.get_torrent(id)
        if not torrent:
            return None
        resp = self.browser.open(torrent.url)
        return resp.content

# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
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

from .pages.index import HomePage
from .pages.torrents import TorrentPage, SearchPage


__all__ = ['T411Browser']


class T411Browser(LoginBrowser):
    PROFILE = Wget()
    TIMEOUT = 30

    BASEURL = 'https://www.t411.in/'
    home = URL('$', HomePage)
    search = URL('torrents/search/\?search=(?P<pattern>.*)&order=seeders&type=desc',
                 SearchPage)
    torrent = URL('/torrents/details/\?id=(?P<id>.*)&r=1',
                  'torrents/[^&]*',
                  TorrentPage)

    #def __init__(self, *args, **kwargs):
    #    Browser.__init__(self, *args, **kwargs)

    def do_login(self):
        self.home.go()
        if not self.page.logged:
            self.page.login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_torrents(self, pattern):
        return self.search.go(pattern=pattern).iter_torrents()

    def get_torrent(self, fullid, torrent=None):
        try:
            self.torrent.go(id=fullid)
            torrent = self.page.get_torrent()
            return torrent
        except BrowserHTTPNotFound:
            return

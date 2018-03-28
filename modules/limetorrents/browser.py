# -*- coding: utf-8 -*-

# Copyright(C) 2018 Julien Veyssier
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
from weboob.browser.profiles import Wget

from .pages import SearchPage, TorrentPage


__all__ = ['LimetorrentsBrowser']


class LimetorrentsBrowser(PagesBrowser):
    PROFILE = Wget()
    TIMEOUT = 30

    BASEURL = 'https://www.limetorrents.cc/'
    search = URL(r'/search/all/(?P<pattern>.*)/seeds/(?P<page>[0-9]+)/', SearchPage)
    torrent = URL(r'/(?P<torrent_name>.*)-torrent-(?P<torrent_id>[0-9]+)\.html', TorrentPage)

    def iter_torrents(self, pattern):
        return self.search.go(pattern=pattern, page=1).iter_torrents()

    def get_torrent(self, id):
        try:
            self.torrent.go(torrent_id=id, torrent_name='whatever')
            torrent = self.page.get_torrent()
            return torrent
        except BrowserHTTPNotFound:
            return

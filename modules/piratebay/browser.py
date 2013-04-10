# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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


import urllib

from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound

from .pages.index import IndexPage
from .pages.torrents import TorrentsPage, TorrentPage


__all__ = ['PiratebayBrowser']


class PiratebayBrowser(BaseBrowser):
    DOMAIN = 'thepiratebay.se'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {'https://thepiratebay.se/': IndexPage,
             'https://thepiratebay.se/search/.*/0/7/0': TorrentsPage,
             'https://thepiratebay.se/torrent/.*': TorrentPage
             }

    def iter_torrents(self, pattern):
        self.location('https://thepiratebay.se/search/%s/0/7/0' % urllib.quote_plus(pattern.encode('utf-8')))

        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        try:
            self.location('https://thepiratebay.se/torrent/%s/' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(TorrentPage):
            return self.page.get_torrent(id)

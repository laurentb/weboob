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


from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound

from .pages.torrents import TorrentsPage, TorrentPage


__all__ = ['IsohuntBrowser']


class IsohuntBrowser(BaseBrowser):
    DOMAIN = 'isohunt.com'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'https://isohunt.com/torrents/.*iht=-1&ihp=1&ihs1=1&iho1=d': TorrentsPage,
        'https://isohunt.com/torrent_details.*tab=summary': TorrentPage,
    }

    def iter_torrents(self, pattern):
        self.location('https://isohunt.com/torrents/%s?iht=-1&ihp=1&ihs1=1&iho1=d' % pattern.encode('utf-8'))
        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        try:
            self.location('https://isohunt.com/torrent_details/%s/?tab=summary' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(TorrentPage):
            return self.page.get_torrent(id)

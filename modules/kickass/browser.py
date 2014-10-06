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


from weboob.deprecated.browser import Browser, BrowserHTTPNotFound

from .pages import TorrentsPage, TorrentPage


__all__ = ['KickassBrowser']


class KickassBrowser(Browser):
    DOMAIN = 'kickass.to'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'https://kickass.to/usearch/.*field=seeders&sorder=desc': TorrentsPage,
        'https://kickass.to/.*.html': TorrentPage,
    }

    def iter_torrents(self, pattern):
        self.location('https://kickass.to/usearch/%s/?field=seeders&sorder=desc' % pattern.encode('utf-8'))
        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        try:
            self.location('https://kickass.to/%s.html' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(TorrentPage):
            return self.page.get_torrent(id)

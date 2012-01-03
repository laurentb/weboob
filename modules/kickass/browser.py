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


from weboob.tools.browser import BaseBrowser

from .pages.torrents import TorrentsPage, TorrentPage


__all__ = ['KickassBrowser']


class KickassBrowser(BaseBrowser):
    DOMAIN = 'kickasstorrents.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'http://fr.(kickasstorrents.com|kat.ph)/new/.*field=seeders&sorder=desc': TorrentsPage,
        'http://fr.(kickasstorrents.com|kat.ph)/.*.html': TorrentPage,
        }

    def home(self):
        return self.location('http://kickasstorrents.com')

    def iter_torrents(self, pattern):
        self.location('http://fr.kickasstorrents.com/new/?q=%s&field=seeders&sorder=desc' % pattern.encode('utf-8'))
        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        self.location('http://fr.kickasstorrents.com/%s.html' % id)
        assert self.is_on_page(TorrentPage)
        return self.page.get_torrent(id)

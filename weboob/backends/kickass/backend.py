# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Veyssier
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from weboob.capabilities.torrent import ICapTorrent
from weboob.tools.backend import BaseBackend

from .browser import KickassBrowser


__all__ = ['KickassBackend']


class KickassBackend(BaseBackend, ICapTorrent):
    NAME = 'kickass'
    MAINTAINER = 'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.5'
    DESCRIPTION = 'kickasstorrent.com bittorrent tracker'
    LICENSE = 'GPLv3'
    BROWSER = KickassBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_torrent(self, id):
        return self.browser.get_torrent(id)

    def get_torrent_file(self, id):
        torrent = self.browser.get_torrent(id)
        if not torrent:
            return None

        return self.browser.openurl(torrent.url.encode('utf-8')).read()

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(pattern.replace(' ','+'))

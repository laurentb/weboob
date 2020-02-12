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

from weboob.capabilities.torrent import CapTorrent, Torrent
from weboob.tools.backend import Module
from weboob.tools.compat import quote_plus

from .browser import CpasbienBrowser


__all__ = ['CpasbienModule']


class CpasbienModule(Module, CapTorrent):
    NAME = 'cpasbien'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'eneiluj@gmx.fr'
    VERSION = '2.0'
    DESCRIPTION = 'Cpasbien Torrents BitTorrent tracker'
    LICENSE = 'AGPLv3+'
    BROWSER = CpasbienBrowser

    def get_torrent(self, id):
        return self.browser.get_torrent(id)

    def get_torrent_file(self, id):
        torrent = self.browser.get_torrent(id)
        if not torrent:
            return None

        resp = self.browser.open(torrent.url)
        return resp.content

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(quote_plus(pattern.encode('utf-8')))

    def fill_torrent(self, torrent, fields):
        if 'description' in fields or 'files' in fields:
            torrent = self.browser.get_torrent(torrent.id)
        return torrent

    OBJECTS = {
        Torrent: fill_torrent
    }

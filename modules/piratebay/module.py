# -*- coding: utf-8 -*-

# Copyright(C) 2010-2017 Julien Veyssier, Laurent Bachelier
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

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.torrent import CapTorrent, MagnetOnly, Torrent
from weboob.tools.backend import BackendConfig, Module
from weboob.tools.value import Value

from .browser import PiratebayBrowser

__all__ = ['PiratebayModule']


class PiratebayModule(Module, CapTorrent):
    NAME = 'piratebay'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '2.1'
    DESCRIPTION = 'The Pirate Bay BitTorrent tracker'
    LICENSE = 'AGPLv3+'
    BROWSER = PiratebayBrowser
    CONFIG = BackendConfig(Value('proxybay', label='Use a Proxy Bay',
                                 regexp=r'https?://.*/', default='', required=False))

    def create_default_browser(self):
        return self.create_browser(self.config['proxybay'].get() or None)

    def get_torrent(self, id):
        return self.browser.get_torrent(id)

    def get_torrent_file(self, id):
        torrent = self.browser.get_torrent(id)
        if not torrent:
            return None

        if torrent.url is NotAvailable and torrent.magnet:
            raise MagnetOnly(torrent.magnet)
        return self.browser.open(torrent.url).content

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(pattern.replace(' ', '+'))

    def fill_torrent(self, torrent, fields):
        if 'description' in fields or 'files' in fields:
            tor = self.get_torrent(torrent.id)
            torrent.description = tor.description
            torrent.magnet = tor.magnet
            torrent.files = tor.files
            torrent.url = tor.url
        return torrent

    OBJECTS = {Torrent: fill_torrent}

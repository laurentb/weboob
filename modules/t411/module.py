# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
# Copyright(C) 2016-2017 David Kremer
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

from weboob.capabilities.torrent import CapTorrent
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.compat import quote_plus
from weboob.tools.value import ValueBackendPassword, Value

from .browser import T411Browser


__all__ = ['T411Module']


class T411Module(Module, CapTorrent):
    NAME = 't411'
    MAINTAINER = u'David Kremer'
    EMAIL = 'courrier@david-kremer.fr'
    VERSION = '1.5'
    DESCRIPTION = 'T411 BitTorrent tracker'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('username', label='Username'), ValueBackendPassword('password', label='Password'))
    BROWSER = T411Browser

    def create_default_browser(self):
        return self.create_browser(self.config['username'].get(), self.config['password'].get())

    def get_torrent(self, torrent):
        return self.browser.get_torrent(torrent)

    def get_torrent_file(self, torrent):
        torrent = self.browser.get_torrent(torrent)
        if not torrent:
            return None

        resp = self.browser.open(torrent.url)
        return resp.content

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(quote_plus(pattern.encode('utf-8')))


# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from weboob.capabilities.torrent import CapTorrent
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import GazelleBrowser


__all__ = ['GazelleModule']


class GazelleModule(Module, CapTorrent):
    NAME = 'gazelle'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = 'Gazelle-based BitTorrent trackers'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('domain',   label='Domain (example "ssl.what.cd")'),
                           Value('protocol', label='Protocol to use', choices=('http', 'https')),
                           Value('username', label='Username'),
                           ValueBackendPassword('password', label='Password'))
    BROWSER = GazelleBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['protocol'].get(), self.config['domain'].get(),
                                   self.config['username'].get(), self.config['password'].get())

    def get_torrent(self, id):
        return self.browser.get_torrent(id)

    def get_torrent_file(self, id):
        torrent = self.browser.get_torrent(id)
        if not torrent:
            return None

        return self.browser.openurl(torrent.url.encode('utf-8')).read()

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(pattern)

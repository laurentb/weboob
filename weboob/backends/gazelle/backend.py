# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

from .browser import GazelleBrowser


__all__ = ['GazelleBackend']


class GazelleBackend(BaseBackend, ICapTorrent):
    NAME = 'gazelle'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.3'
    DESCRIPTION = 'gazelle bittorrent tracker'
    LICENSE = 'GPLv3'
    CONFIG = {'username': BaseBackend.ConfigField(description='Username on website'),
              'password': BaseBackend.ConfigField(description='Password of account', is_masked=True),
              'protocol': BaseBackend.ConfigField(description='Protocol to use', choices=('http', 'https')),
              'domain': BaseBackend.ConfigField(description='Domain (example "ssl.what.cd")'),
             }
    BROWSER = GazelleBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['protocol'], self.config['domain'],
                                   self.config['username'], self.config['password'])

    def get_torrent(self, id):
        return self.browser.get_torrent(id)

    def get_torrent_file(self, id):
        torrent = self.browser.get_torrent(id)
        if not torrent:
            return None

        return self.browser.openurl(torrent.url.encode('utf-8')).read()

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(pattern)

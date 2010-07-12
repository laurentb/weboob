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

from __future__ import with_statement

import sys

from weboob.capabilities.torrent import ICapTorrent
from weboob.tools.application.console import ConsoleApplication


__all__ = ['Weboorrents']


class Weboorrents(ConsoleApplication):
    APPNAME = 'weboorrents'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def main(self, argv):
        self.load_configured_backends(ICapTorrent)
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Get information about a torrent')
    def command_info(self, id):
        _id, backend_name = self.parse_id(id)

        found = 0
        for backend, torrent in self.weboob.do_backends(backend_name, 'get_torrent', _id):
            if torrent:
                self.format(torrent, backend.name)
                found = 1

        if not found:
            print >>sys.stderr, 'Torrent "%s" not found' % id

    @ConsoleApplication.command('Get the torrent file')
    def command_getfile(self, id, dest):
        _id, backend_name = self.parse_id(id)

        for backend, buf in self.weboob.do_backends(backend_name, 'get_torrent_file', _id):
            if buf:
                if dest == '-':
                    print buf
                else:
                    with open(dest, 'w') as f:
                        f.write(buf)
                return

        print >>sys.stderr, 'Torrent "%s" not found' % id

    @ConsoleApplication.command('Search torrents')
    def command_search(self, pattern=None):
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Last torrents')
        for backend, torrent in self.weboob.do('iter_torrents', pattern=pattern):
            self.format(torrent, backend.name)

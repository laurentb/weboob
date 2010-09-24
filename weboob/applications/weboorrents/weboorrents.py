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
from weboob.tools.application.repl import ReplApplication


__all__ = ['Weboorrents']


class Weboorrents(ReplApplication):
    APPNAME = 'weboorrents'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def load_default_backends(self):
        self.load_backends(ICapTorrent)

    def do_info(self, id):
        """
        info ID

        Get information about a torrent.
        """
        _id, backend_name = self.parse_id(id)

        found = 0
        for backend, torrent in self.do('get_torrent', _id, backends=backend_name):
            if torrent:
                self.format(torrent)
                found = 1

        if not found:
            print >>sys.stderr, 'Torrent "%s" not found' % id

    def do_getfile(self, line):
        """
        getfile ID FILENAME

        Get the .torrent file.
        FILENAME is where to write the file. If FILENAME is '-',
        the file is written to stdout.
        """
        id, dest = self.parseline(line, 2, 2)

        _id, backend_name = self.parse_id(id)

        for backend, buf in self.do('get_torrent_file', _id, backends=backend_name):
            if buf:
                if dest == '-':
                    print buf
                else:
                    with open(dest, 'w') as f:
                        f.write(buf)
                return

        print >>sys.stderr, 'Torrent "%s" not found' % id

    def do_search(self, pattern):
        """
        search [PATTERN]

        Search torrents.
        """
        if not pattern:
            pattern = None
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Latest torrents')
        for backend, torrent in self.do('iter_torrents', pattern=pattern):
            self.format(torrent)

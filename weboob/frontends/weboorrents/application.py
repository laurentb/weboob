# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from __future__ import with_statement

import logging

from weboob.capabilities.torrent import ICapTorrent
from weboob.tools.application import ConsoleApplication


__all__ = ['Weboorrents']


class Weboorrents(ConsoleApplication):
    APPNAME = 'weboorrents'
    VERSION = '1.0'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    CONFIG = {}

    def main(self, argv):
        self.load_backends(ICapTorrent)
        return self.process_command(*argv[1:])

    def split_id(self, id):
        if not '.' in id:
            logging.error('ID must be in form <backend>.<ID>')
            return None, None

        backend_name, id = id.split('.', 1)
        backend = self.weboob.backends.get(backend_name, None)
        if not backend:
            logging.error('Backends "%s" not found' % backend_name)
            return None, None

        return backend, id

    @ConsoleApplication.command('Get information about a torrent')
    def command_info(self, id):
        backend, id = self.split_id(id)
        if not backend:
            return 1
        with backend:
            torrent = backend.get_torrent(id)
            if not torrent:
                logging.error('Torrent "%s" not found' % id)
                return 1
            print self.format(torrent)

    @ConsoleApplication.command('Get the torrent file')
    def command_getfile(self, id, dest):
        backend, id = self.split_id(id)
        if not backend:
            return 1

        with backend:
            s = backend.get_torrent_file(id)
            if not s:
                logging.error('Torrent "%s" not found' % id)
                return 1

            if dest == '-':
                print s
            else:
                with open(dest, 'w') as f:
                    f.write(s)

    @ConsoleApplication.command('Search torrents')
    def command_search(self, pattern=None):
        print u'Search pattern: %s' % pattern if pattern else u'Last torrents'
        for backend, torrent in self.weboob.do('iter_torrents', pattern=pattern):
            print self.format(torrent)

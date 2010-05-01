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

import sys

from weboob.capabilities.torrent import ICapTorrent
from weboob.tools.application import ConsoleApplication

class Weboorrents(ConsoleApplication):
    APPNAME = 'weboorrents'
    VERSION = '1.0'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    CONFIG = {}

    def main(self, argv):
        self.load_backends(ICapTorrent)
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Get information about a torrent')
    def command_info(self, id):
        if not '.' in id:
            print >>sys.stderr, 'ID must be in form <backend>.<ID>'
            return 1

        backend_name, id = id.split('.', 1)
        backend = self.weboob.backends.get(backend_name, None)
        if not backend:
            print >>sys.stderr, 'Backends "%s" not found' % backend_name
            return 1

        with backend:
            torrent = backend.get_torrent(id)

            if not torrent:
                print >>sys.stderr, 'Torrent "%s" not found' % id
                return 1

            rows = []
            rows.append(('ID', torrent.id))
            rows.append(('Name', torrent.name))
            rows.append(('Size', torrent.size))
            return {backend.name: rows}

    @ConsoleApplication.command('Search torrents')
    def command_search(self, pattern=None):
        results = {}
        if pattern:
            results['BEFORE'] = u'Search pattern: %s' % pattern
        else:
            results['BEFORE'] = u'Last videos'
        results['HEADER'] = ('ID', 'Name', 'Size')

        for backend, torrent in self.weboob.do('iter_torrents', pattern=pattern):
            row = ('%s.%s' % (backend.name,torrent.id), torrent.name, torrent.size)
            try:
                results[backend.name].append(row)
            except KeyError:
                results[backend.name] = [row]
        return results

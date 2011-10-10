# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

from __future__ import with_statement

import sys

from weboob.capabilities.torrent import ICapTorrent
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Weboorrents']


def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%-4.1f%s" % (num, x)
        num /= 1024.0


class TorrentInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'size', 'seeders', 'leechers', 'url', 'files', 'description')

    def flush(self):
        pass

    def format_dict(self, item):
        result = u'%s%s%s\n' % (self.BOLD, item['name'], self.NC)
        result += 'ID: %s\n' % item['id']
        result += 'Size: %s\n' % sizeof_fmt(item['size'])
        result += 'Seeders: %s\n' % item['seeders']
        result += 'Leechers: %s\n' % item['leechers']
        result += 'URL: %s\n' % item['url']
        if item['files']:
            result += '\n%sFiles%s\n' % (self.BOLD, self.NC)
            for f in item['files']:
                result += ' * %s\n' % f
        result += '\n%sDescription%s\n' % (self.BOLD, self.NC)
        result += item['description']
        return result


class TorrentListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'size', 'seeders', 'leechers')

    count = 0

    def flush(self):
        self.count = 0
        pass

    def format_dict(self, item):
        self.count += 1
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s (%s)%s\n' % (self.BOLD, self.count, item['name'], backend, self.NC)
        else:
            result = u'%s* (%s) %s%s\n' % (self.BOLD, item['id'], item['name'], self.NC)
        size = sizeof_fmt(item['size'])
        result += '  %10s   (Seed: %2d / Leech: %2d)' % (size, item['seeders'], item['leechers'])
        return result


class Weboorrents(ReplApplication):
    APPNAME = 'weboorrents'
    VERSION = '0.9'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to search for torrents on various trackers ' \
                  'and download .torrent files.'
    CAPS = ICapTorrent
    EXTRA_FORMATTERS = {'torrent_list': TorrentListFormatter,
                        'torrent_info': TorrentInfoFormatter,
                       }
    COMMANDS_FORMATTERS = {'search':    'torrent_list',
                           'info':      'torrent_info',
                          }

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

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
            return 3
        else:
            self.flush()

    def complete_getfile(self, text, line, *ignored):
        args = line.split(' ', 2)
        if len(args) == 2:
            return self._complete_object()
        elif len(args) >= 3:
            return self.path_completer(args[2])

    def do_getfile(self, line):
        """
        getfile ID [FILENAME]

        Get the .torrent file.
        FILENAME is where to write the file. If FILENAME is '-',
        the file is written to stdout.
        """
        id, dest = self.parse_command_args(line, 2, 1)

        _id, backend_name = self.parse_id(id)

        if dest is None:
            dest = '%s.torrent' % _id

        for backend, buf in self.do('get_torrent_file', _id, backends=backend_name):
            if buf:
                if dest == '-':
                    print buf
                else:
                    try:
                        with open(dest, 'w') as f:
                            f.write(buf)
                    except IOError, e:
                        print >>sys.stderr, 'Unable to write .torrent in "%s": %s' % (dest, e)
                        return 1
                return

        print >>sys.stderr, 'Torrent "%s" not found' % id
        return 3

    def do_search(self, pattern):
        """
        search [PATTERN]

        Search torrents.
        """
        self.change_path('/search')
        if not pattern:
            pattern = None
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Latest torrents')
        for backend, torrent in self.do('iter_torrents', pattern=pattern):
            self.add_object(torrent)
            self.format(torrent)
        self.flush()

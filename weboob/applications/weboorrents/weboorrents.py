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
        result = u'%s%s%s\n' % (ReplApplication.BOLD, item['name'], ReplApplication.NC)
        result += 'ID: %s\n' % item['id']
        result += 'Size: %s\n' % sizeof_fmt(item['size'])
        result += 'Seeders: %s\n' % item['seeders']
        result += 'Leechers: %s\n' % item['leechers']
        result += 'URL: %s\n' % item['url']
        result += '\n%sFiles%s\n' % (ReplApplication.BOLD, ReplApplication.NC)
        for f in item['files']:
            result += ' * %s\n' % f
        result += '\n%sDescription%s\n' % (ReplApplication.BOLD, ReplApplication.NC)
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
            result = u'%s* (%d) %s (%s)%s\n' % (ReplApplication.BOLD, self.count, item['name'], backend, ReplApplication.NC)
        else:
            result = u'%s* (%s) %s%s\n' % (ReplApplication.BOLD, item['id'], item['name'], ReplApplication.NC)
        size = sizeof_fmt(item['size'])
        result += '  %10s   (Seed: %2d / Leech: %2d)' % (size, item['seeders'], item['leechers'])
        return result


class Weboorrents(ReplApplication):
    APPNAME = 'weboorrents'
    VERSION = '0.6'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    DESCRIPTION = "Weboorrents is a console application to search torrents on supported trackers " \
                  "and to download .torrent files."
    CAPS = ICapTorrent
    EXTRA_FORMATTERS = {'torrent_list': TorrentListFormatter,
                        'torrent_info': TorrentInfoFormatter,
                       }
    COMMANDS_FORMATTERS = {'search':    'torrent_list',
                           'info':      'torrent_info',
                          }

    torrents = []

    def _complete_id(self):
        return ['%s@%s' % (torrent.id, torrent.backend) for torrent in self.torrents]

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_id()

    def parse_id(self, id):
        if self.interactive:
            try:
                torrent = self.torrents[int(id) - 1]
            except (IndexError,ValueError):
                pass
            else:
                id = '%s@%s' % (torrent.id, torrent.backend)
        return ReplApplication.parse_id(self, id)

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
        else:
            self.flush()

    def complete_getfile(self, text, line, *ignored):
        args = line.split(' ', 2)
        if len(args) == 2:
            return self._complete_id()
        elif len(args) >= 3:
            return self.path_completer(args[2])

    def do_getfile(self, line):
        """
        getfile ID FILENAME

        Get the .torrent file.
        FILENAME is where to write the file. If FILENAME is '-',
        the file is written to stdout.
        """
        id, dest = self.parse_command_args(line, 2, 2)

        _id, backend_name = self.parse_id(id)

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

    def do_search(self, pattern):
        """
        search [PATTERN]

        Search torrents.
        """
        self.torrents = []
        if not pattern:
            pattern = None
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Latest torrents')
        for backend, torrent in self.do('iter_torrents', pattern=pattern):
            self.torrents.append(torrent)
            self.format(torrent)
        self.flush()

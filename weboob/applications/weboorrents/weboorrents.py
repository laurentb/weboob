# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon
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

from weboob.capabilities.torrent import ICapTorrent, MagnetOnly
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter
from weboob.core import CallErrors


__all__ = ['Weboorrents']


def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%-4.1f%s" % (num, x)
        num /= 1024.0


class TorrentInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'size', 'seeders', 'leechers', 'url', 'files', 'description')

    def format_obj(self, obj, alias):
        result = u'%s%s%s\n' % (self.BOLD, obj.name, self.NC)
        result += 'ID: %s\n' % obj.fullid
        result += 'Size: %s\n' % sizeof_fmt(obj.size)
        result += 'Seeders: %s\n' % obj.seeders
        result += 'Leechers: %s\n' % obj.leechers
        result += 'URL: %s\n' % obj.url
        if hasattr(obj, 'magnet') and obj.magnet:
            result += 'Magnet URL: %s\n' % obj.magnet
        if obj.files:
            result += '\n%sFiles%s\n' % (self.BOLD, self.NC)
            for f in obj.files:
                result += ' * %s\n' % f
        result += '\n%sDescription%s\n' % (self.BOLD, self.NC)
        result += obj.description
        return result


class TorrentListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'size', 'seeders', 'leechers')

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        size = sizeof_fmt(obj.size)
        return '%10s   (Seed: %2d / Leech: %2d)' % (size, obj.seeders, obj.leechers)


class Weboorrents(ReplApplication):
    APPNAME = 'weboorrents'
    VERSION = '0.e'
    COPYRIGHT = 'Copyright(C) 2010-2012 Romain Bignon'
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

        torrent = self.get_object(id, 'get_torrent')
        if not torrent:
            print >>sys.stderr, 'Torrent not found: %s' %  id
            return 3

        self.start_format()
        self.format(torrent)
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

        try:
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
        except CallErrors, errors:
            for backend, error, backtrace in errors:
                if isinstance(error, MagnetOnly):
                    print >>sys.stderr, u'Error(%s): No direct URL available, ' \
                    u'please provide this magnet URL ' \
                    u'to your client:\n%s' % (backend, error.magnet)
                    return 4
                else:
                    self.bcall_error_handler(backend, error, backtrace)

        print >>sys.stderr, 'Torrent "%s" not found' % id
        return 3

    def do_search(self, pattern):
        """
        search [PATTERN]

        Search torrents.
        """
        self.change_path([u'search'])
        if not pattern:
            pattern = None

        self.start_format(pattern=pattern)
        for backend, torrent in self.do('iter_torrents', pattern=pattern):
            self.cached_format(torrent)
        self.flush()

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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

from weboob.capabilities.subtitle import ICapSubtitle
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter
from weboob.core import CallErrors


__all__ = ['Suboob']


def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%-4.1f%s" % (num, x)
        num /= 1024.0


class SubtitleListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'url', 'fps')

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        return '(%s fps)' % (obj.fps)


class Suboob(ReplApplication):
    APPNAME = 'suboob'
    VERSION = '0.f'
    COPYRIGHT = 'Copyright(C) 2010-2012 Julien Veyssier'
    DESCRIPTION = "Console application allowing to search for subtitles on various services " \
                  "and download them."
    SHORT_DESCRIPTION = "search and download subtitles"
    CAPS = ICapSubtitle
    EXTRA_FORMATTERS = {'subtitle_list': SubtitleListFormatter
                       }
    COMMANDS_FORMATTERS = {'search':    'subtitle_list',
                          }

    def complete_getfile(self, text, line, *ignored):
        args = line.split(' ', 2)
        if len(args) == 2:
            return self._complete_object()
        elif len(args) >= 3:
            return self.path_completer(args[2])

    def do_getfile(self, line):
        """
        getfile ID [FILENAME]

        Get the subtitle or archive file.
        FILENAME is where to write the file. If FILENAME is '-',
        the file is written to stdout.
        """
        id, dest = self.parse_command_args(line, 2, 1)

        _id, backend_name = self.parse_id(id)

        if dest is None:
            dest = '%s' % _id

        try:
            for backend, buf in self.do('get_subtitle_file', _id, backends=backend_name):
                if buf:
                    if dest == '-':
                        print buf
                    else:
                        try:
                            with open(dest, 'w') as f:
                                f.write(buf)
                        except IOError, e:
                            print >>sys.stderr, 'Unable to write file in "%s": %s' % (dest, e)
                            return 1
                    return
        except CallErrors, errors:
            for backend, error, backtrace in errors:
                self.bcall_error_handler(backend, error, backtrace)

        print >>sys.stderr, 'Subtitle "%s" not found' % id
        return 3

    def do_search(self, pattern):
        """
        search [PATTERN]

        Search subtitles.
        """
        self.change_path([u'search'])
        if not pattern:
            pattern = None

        self.start_format(pattern=pattern)
        for backend, subtitle in self.do('iter_subtitles', pattern=pattern):
            self.cached_format(subtitle)
        self.flush()

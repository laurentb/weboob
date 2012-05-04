# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Christophe Benz
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

import os
import sys
import subprocess
if sys.platform == 'win32':
    import WConio

try:
    import tty, termios
except ImportError:
    PROMPT = '--Press return to continue--'
    def readch():
        return sys.stdin.readline()
else:
    PROMPT = '--Press a key to continue--'
    def readch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            c = sys.stdin.read(1)
            # XXX do not read magic number
            if c == '\x03':
                raise KeyboardInterrupt()
            return c
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

from weboob.capabilities.base import CapBaseObject
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.application.console import ConsoleApplication


__all__ = ['IFormatter', 'MandatoryFieldsNotFound']


class MandatoryFieldsNotFound(Exception):
    def __init__(self, missing_fields):
        Exception.__init__(self, u'Mandatory fields not found: %s.' % ', '.join(missing_fields))


class IFormatter(object):
    MANDATORY_FIELDS = None

    def get_bold(self):
        if self.outfile != sys.stdout:
            return ''
        else:
            return ConsoleApplication.BOLD

    def get_nc(self):
        if self.outfile != sys.stdout:
            return ''
        else:
            return ConsoleApplication.NC

    BOLD = property(get_bold)
    NC = property(get_nc)

    def __init__(self, display_keys=True, display_header=True, outfile=sys.stdout):
        self.display_keys = display_keys
        self.display_header = display_header
        self.interactive = False
        self.print_lines = 0
        self.termrows = 0
        self.outfile = outfile
        # XXX if stdin is not a tty, it seems that the command fails.

        if os.isatty(sys.stdout.fileno()) and os.isatty(sys.stdin.fileno()):
            if sys.platform == 'win32':
                self.termrows = WConio.gettextinfo()[8]
            else:
                self.termrows = int(subprocess.Popen('stty size', shell=True, stdout=subprocess.PIPE).communicate()[0].split()[0])

    def output(self, formatted):
        if self.outfile != sys.stdout:
            with open(self.outfile, "a+") as outfile:
                outfile.write(formatted.encode('utf-8'))

        else:
            for line in formatted.split('\n'):
                if self.termrows and (self.print_lines + 1) >= self.termrows:
                    self.outfile.write(PROMPT)
                    self.outfile.flush()
                    readch()
                    self.outfile.write('\b \b' * len(PROMPT))
                    self.print_lines = 0

                if isinstance(line, unicode):
                    line = line.encode('utf-8')
                print line
                self.print_lines += 1

    def start_format(self, **kwargs):
        pass

    def flush(self):
        pass

    def format(self, obj, selected_fields=None, alias=None):
        """
        Format an object to be human-readable.
        An object has fields which can be selected.

        :param obj: object to format
        :type obj: CapBaseObject or dict
        :param selected_fields: fields to display. If None, all fields are selected
        :type selected_fields: tuple
        :param alias: an alias to use instead of the object's ID
        :type alias: unicode
        """
        if isinstance(obj, CapBaseObject):
            if selected_fields is not None and not '*' in selected_fields:
                obj = obj.copy()
                for name, value in obj.iter_fields():
                    if not name in selected_fields:
                        delattr(obj, name)

            if self.MANDATORY_FIELDS:
                missing_fields = set(self.MANDATORY_FIELDS) - set([name for name, value in obj.iter_fields()])
                if missing_fields:
                    raise MandatoryFieldsNotFound(missing_fields)

            formatted = self.format_obj(obj, alias)
        else:
            obj = self.to_dict(obj)

            if selected_fields is not None and not '*' in selected_fields:
                obj = obj.copy()
                for name, value in obj.iteritems():
                    if not name in selected_fields:
                        obj.pop(name)

            if self.MANDATORY_FIELDS:
                missing_fields = set(self.MANDATORY_FIELDS) - set(obj.iterkeys())
                if missing_fields:
                    raise MandatoryFieldsNotFound(missing_fields)

            formatted = self.format_dict(obj)

        if formatted:
            self.output(formatted)
        return formatted


    def format_obj(self, obj, alias=None):
        """
        Format an object to be human-readable.
        Called by format().
        This method has to be overridden in child classes.

        :param obj: object to format
        :type obj: CapBaseObject
        :rtype: str
        """
        return self.format_dict(self.to_dict(obj))

    def format_dict(self, obj):
        """
        Format a dict to be human-readable.

        :param obj: dict to format
        :type obj: dict
        :rtype: str
        """
        return NotImplementedError()

    def to_dict(self, obj):
        if not isinstance(obj, CapBaseObject):
            try:
                return OrderedDict(obj)
            except ValueError:
                raise TypeError('Please give a CapBaseObject or a dict')

        def iter_decorate(d):
            for key, value in d:
                if key == 'id' and obj.backend is not None:
                    value = obj.fullid
                yield key, value

        fields_iterator = obj.iter_fields()
        return OrderedDict(iter_decorate(fields_iterator))


class PrettyFormatter(IFormatter):
    def format_obj(self, obj, alias):
        title = self.get_title(obj)
        desc = self.get_description(obj)

        if desc is None:
            title = '%s%s%s' % (self.NC, title, self.BOLD)

        if alias is not None:
            result = u'%s* (%s) %s (%s)%s' % (self.BOLD, alias, title, obj.backend, self.NC)
        else:
            result = u'%s* (%s) %s%s' % (self.BOLD, obj.fullid, title, self.NC)

        if desc is not None:
            result += u'\n\t%s' % desc

        return result

    def get_title(self, obj):
        raise NotImplementedError()

    def get_description(self, obj):
        return None

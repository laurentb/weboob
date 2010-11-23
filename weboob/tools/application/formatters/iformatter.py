# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


import os
import sys
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

from weboob.capabilities.base import CapBaseObject, FieldNotFound
from weboob.tools.ordereddict import OrderedDict


__all__ = ['IFormatter', 'MandatoryFieldsNotFound']


class MandatoryFieldsNotFound(Exception):
    def __init__(self, missing_fields):
        Exception.__init__(self, u'Mandatory fields not found: %s.' % ','.join(missing_fields))


class IFormatter(object):

    MANDATORY_FIELDS = None

    def __init__(self, display_keys=True, display_header=True, return_only=False):
        self.display_keys = display_keys
        self.display_header = display_header
        self.return_only = return_only
        self.interactive = False
        self.print_lines = 0
        self.termrows = 0
        # XXX if stdin is not a tty, it seems that the command fails.
        if os.isatty(sys.stdout.fileno()) and os.isatty(sys.stdin.fileno()):
            self.termrows = int(os.popen('stty size', 'r').read().split()[0])

    def after_format(self, formatted):
        for line in formatted.split('\n'):
            if self.termrows and (self.print_lines + 1) >= self.termrows:
                sys.stdout.write(PROMPT)
                sys.stdout.flush()
                readch()
                sys.stdout.write('\b \b' * len(PROMPT))
                self.print_lines = 0

            if isinstance(line, unicode):
                line = line.encode('utf-8')
            print line
            self.print_lines += 1

    def build_id(self, v, backend_name):
        return u'%s@%s' % (unicode(v), backend_name)

    def flush(self):
        raise NotImplementedError()

    def format(self, obj, selected_fields=None):
        """
        Format an object to be human-readable.
        An object has fields which can be selected.
        If the object provides an iter_fields() method, the formatter will
        call it. It can be used to specify the fields order.

        @param obj  [object] object to format
        @param selected_fields  [tuple] fields to display. If None, all fields are selected
        @return  a string of the formatted object
        """
        assert isinstance(obj, (dict, CapBaseObject, tuple))

        if isinstance(obj, dict):
            item = obj
        elif isinstance(obj, tuple):
            item = OrderedDict([(k, v) for k, v in obj])
        else:
            item = self.to_dict(obj, selected_fields)

        if item is None:
            return None

        if self.MANDATORY_FIELDS:
            missing_fields = set(self.MANDATORY_FIELDS) - set(item.keys())
            if missing_fields:
                raise MandatoryFieldsNotFound(missing_fields)

        formatted = self.format_dict(item=item)
        if formatted:
            self.after_format(formatted)
        return formatted

    def format_dict(self, item):
        """
        Format a dict to be human-readable. The dict is already simplified
        if user provides selected fields.
        Called by format().
        This method has to be overridden in child classes.

        @param item  [dict] item to format
        @return  a string of the formatted dict
        """
        raise NotImplementedError()

    def set_header(self, string):
        if self.display_header:
            print string.encode('utf-8')

    def to_dict(self, obj, selected_fields=None):
        def iter_select(d):
            if selected_fields is None or '*' in selected_fields:
                fields = d.iterkeys()
            else:
                fields = selected_fields

            for key in fields:
                try:
                    value = d[key]
                except KeyError:
                    raise FieldNotFound(obj, key)

                yield key, value

        def iter_decorate(d):
            for key, value in d:
                if key == 'id' and obj.backend is not None:
                    value = self.build_id(value, obj.backend)
                yield key, value

        fields_iterator = obj.iter_fields()
        d = OrderedDict(iter_decorate(fields_iterator))
        return OrderedDict((k, v) for k, v in iter_select(d))

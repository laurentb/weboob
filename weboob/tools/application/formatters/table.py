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


from prettytable import PrettyTable

from weboob.capabilities.base import NotLoaded, NotAvailable

from .iformatter import IFormatter


__all__ = ['TableFormatter', 'HTMLTableFormatter']


class TableFormatter(IFormatter):
    HTML = False

    def __init__(self, display_keys=True, return_only=False):
        IFormatter.__init__(self, display_keys=display_keys, return_only=return_only)
        self.queue = []
        self.keys = None
        self.header = None

    def after_format(self, formatted):
        if self.keys is None:
            self.keys = formatted.keys()
        self.queue.append(formatted.values())

    def flush(self):
        if len(self.queue) == 0:
            return

        queue = [() for i in xrange(len(self.queue))]
        column_headers = []
        # Do not display columns when all values are NotLoaded or NotAvailable
        for i in xrange(len(self.keys)):
            available = False
            for line in self.queue:
                if line[i] is not NotLoaded and line[i] is not NotAvailable and line[i] is not None:
                    available = True
                    break
            if available:
                column_headers.append(self.keys[i].capitalize().replace('_', ' '))
                for j in xrange(len(self.queue)):
                    queue[j] += (self.queue[j][i],)

        s = ''
        if self.display_header and self.header:
            if self.HTML:
                s+= '<p>%s</p>' % self.header
            else:
                s += self.header
            s += "\n"
        table = PrettyTable(list(column_headers))
        for column_header in column_headers:
            table.set_field_align(column_header, 'l')
        for line in queue:
            table.add_row(line)

        if self.HTML:
            s += table.get_html_string()
        else:
            s += table.get_string()
        if self.return_only:
            return s
        else:
            print s.encode('utf-8')

    def format_dict(self, item):
        # format is done in self.flush() by prettytable
        return item

    def set_header(self, string):
        self.header = string

class HTMLTableFormatter(TableFormatter):
    HTML = True

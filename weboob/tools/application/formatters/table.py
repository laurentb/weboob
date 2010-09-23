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

from .iformatter import IFormatter


__all__ = ['TableFormatter']


class TableFormatter(IFormatter):
    column_headers = None
    queue = []
    header = None

    def __init__(self, display_keys=True, return_only=False, result_funcname='get_string'):
        IFormatter.__init__(self, display_keys=display_keys, return_only=return_only)
        self.result_funcname = result_funcname

    def after_format(self, formatted):
        if self.column_headers is None:
            self.column_headers = formatted.keys()
        self.queue.append(formatted.values())

    def flush(self):
        if self.column_headers is None:
            return None
        s = ''
        if self.display_header and self.header:
            if self.result_funcname == 'get_string':
                s += self.header
            elif self.result_funcname == 'get_html_string':
                s+= '<p>%s</p>' % self.header
            s += "\n"
        table = PrettyTable(list(self.column_headers))
        for column_header in self.column_headers:
            table.set_field_align(column_header, 'l')
        for line in self.queue:
            table.add_row(line)
        s += getattr(table, self.result_funcname)()
        if self.return_only:
            return s
        else:
            print s.encode('utf-8')
        self.queue = []

    def format_dict(self, item):
        # format is done in self.flush() by prettytable
        return item

    def set_header(self, string):
        self.header = string

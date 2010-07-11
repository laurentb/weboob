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


__all__ = ['load_formatter']


formatters = ('htmltable', 'multiline', 'simple', 'table', 'webkit')
            

def load_formatter(name):
    if name not in formatters:
        raise Exception(u'Formatter "%s" not found' % name)
    if name in ('htmltable', 'table'):
        from .table import TableFormatter
        if name == 'htmltable':
            return TableFormatter(result_funcname='get_html_string')
        elif name == 'table':
            return TableFormatter()
    elif name == 'simple':
        from .simple import SimpleFormatter
        return SimpleFormatter()
    elif name == 'multiline':
        from .multiline import MultilineFormatter
        return MultilineFormatter()
    elif name == 'webkit':
        from .webkit import WebkitGtkFormatter
        return WebkitGtkFormatter()

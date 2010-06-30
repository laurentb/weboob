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


from .iformatter import IFormatter


__all__ = ['SimpleFormatter']


class SimpleFormatter(IFormatter):
    def __init__(self, field_separator=u'\t', key_value_separator=u'='):
        IFormatter.__init__(self)
        self.field_separator = field_separator
        self.key_value_separator = key_value_separator

    def after_format(self, formatted):
        print formatted.encode('utf-8')

    def flush(self):
        pass

    def format_dict(self, item):
        return self.field_separator.join(u'%s%s' % ((u'%s%s' % (k, self.key_value_separator) if self.display_keys else ''), v) for k, v in item.iteritems())

    def set_header(self, string):
        print string.encode('utf-8')

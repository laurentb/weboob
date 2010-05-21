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


__all__ = ['MultilineFormatter']


class MultilineFormatter(IFormatter):
    def __init__(self, key_value_separator=u': ', after_item=u'\n', display_keys=True):
        self.key_value_separator = key_value_separator
        self.after_item = after_item
        self.display_keys = display_keys

    def format_dict(self, item, selected_fields):
        result_str = u'\n'.join(u'%s%s' % ((u'%s%s' % (k, self.key_value_separator) if self.display_keys else ''),
                                           unicode(item[k])) for k in selected_fields) + self.after_item
        return result_str

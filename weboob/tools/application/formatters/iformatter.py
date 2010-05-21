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


import types


__all__ = ['IFormatter']


class IFormatter(object):
    def format(self, obj, selected_fields=None, condition=None):
        """
        Format an object to be human-readable.
        An object has fields which can be selected, and the objects
        can be filtered using a condition (like SELECT and WHERE in SQL).
        If the object provides an iter_fields() method, the formatter will
        call it. It can be used to specify the fields order.

        @param obj  [object] object to format
        @param selected_fields  [list] fields to display
        @param condition  [Condition] condition to objects to display 
        @return  a string of the formatted object
        """
        item = self.to_dict(obj, condition)
        if selected_fields is None:
            selected_fields = sorted(item)
        return self.format_dict(item=item, selected_fields=selected_fields)

    def format_dict(self, item, selected_fields):
        """
        Format an dict to be human-readable.
        Called by format().
        This method has to be overridden in child classes.

        @param item  [dict] item to format
        @param selected_fields  [list] fields to display
        @return  a string of the formatted dict
        """
        raise NotImplementedError()

    def iter_fields(self, obj):
        for attribute_name in dir(obj):
            if attribute_name.startswith('_'):
                continue
            attribute = getattr(obj, attribute_name)
            if not isinstance(attribute, types.MethodType):
                yield attribute_name, attribute

    def to_dict(self, obj, condition=None):
        fields_iterator = obj.iter_fields() if hasattr(obj, 'iter_fields') else self.iter_fields(obj)
        d = dict((k, v) for k, v in fields_iterator)
        if condition is not None:
            if not condition.is_valid(d):
                d = None
        return d

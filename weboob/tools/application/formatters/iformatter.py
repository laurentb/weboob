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
    def __init__(self, display_keys=True, return_only=False):
        self.display_keys = display_keys
        self.return_only = return_only

    def after_format(self, formatted):
        raise NotImplementedError()

    def flush(self):
        raise NotImplementedError()

    def format(self, obj, backend_name=None, selected_fields=None, condition=None):
        """
        Format an object to be human-readable.
        An object has fields which can be selected, and the objects
        can be filtered using a condition (like SELECT and WHERE in SQL).
        If the object provides an iter_fields() method, the formatter will
        call it. It can be used to specify the fields order.

        @param obj  [object] object to format
        @param selected_fields  [list] fields to display. If None, all fields are selected.
        @param condition  [Condition] condition to objects to display
        @return  a string of the formatted object
        """
        if isinstance(obj, dict):
            item = obj
        else:
            item = self.to_dict(obj, backend_name, condition, selected_fields)
        if item is None:
            return None
        formatted = self.format_dict(item=item)
        if formatted:
            self.after_format(formatted)
        return formatted

    def format_dict(self, item):
        """
        Format an dict to be human-readable. The dict is already simplified if user provides selected fields.
        Called by format().
        This method has to be overridden in child classes.

        @param item  [dict] item to format
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

    def set_header(self, string):
        raise NotImplementedError()

    def to_dict(self, obj, backend_name=None, condition=None, selected_fields=None):
        def iter_select_and_decorate(d):
            if hasattr(obj, '__id__'):
                id_attr = getattr(obj, '__id__')
                if not isinstance(id_attr, (set, list, tuple)):
                    id_attr = (id_attr,)
                id_fields = id_attr
            else:
                id_fields = ('id',)
            for k, v in d:
                if selected_fields is not None and k not in selected_fields:
                    continue
                if k in id_fields and backend_name is not None:
                    v = u'%s@%s' % (unicode(v), backend_name)
                yield k, v
        fields_iterator = obj.iter_fields() if hasattr(obj, 'iter_fields') else self.iter_fields(obj)
        d = dict((k, v) for k, v in iter_select_and_decorate(fields_iterator))
        if condition is not None and not condition.is_valid(d):
            d = None
        return d

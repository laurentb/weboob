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


from weboob.capabilities.base import CapBaseObject
from weboob.tools.ordereddict import OrderedDict


__all__ = ['FieldNotFound', 'IFormatter']


class FieldNotFound(Exception):
    def __init__(self, field):
        Exception.__init__(self, u'Field not found: "%s"' % field)


class IFormatter(object):
    def __init__(self, display_keys=True, display_header=True, return_only=False):
        self.display_keys = display_keys
        self.display_header = display_header
        self.return_only = return_only

    def after_format(self, formatted):
        raise NotImplementedError()

    def build_id(self, v, backend_name):
        return u'%s@%s' % (unicode(v), backend_name)

    def flush(self):
        raise NotImplementedError()

    def format(self, obj, selected_fields=None, condition=None):
        """
        Format an object to be human-readable.
        An object has fields which can be selected, and the objects
        can be filtered using a condition (like SELECT and WHERE in SQL).
        If the object provides an iter_fields() method, the formatter will
        call it. It can be used to specify the fields order.

        @param obj  [object] object to format
        @param selected_fields  [tuple] fields to display. If None, all fields are selected
        @param condition  [Condition] condition to objects to display
        @return  a string of the formatted object
        """
        assert isinstance(obj, (dict, CapBaseObject, tuple))

        if isinstance(obj, dict):
            item = obj
        elif isinstance(obj, tuple):
            item = OrderedDict([(k, v) for k, v in obj])
        else:
            item = self.to_dict(obj, condition, selected_fields)

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

    def set_header(self, string):
        raise NotImplementedError()

    def to_dict(self, obj, condition=None, selected_fields=None):
        def iter_select_and_decorate(d):
            if selected_fields is None or '*' in selected_fields:
                fields = d.iterkeys()
            else:
                fields = selected_fields

            for key in fields:
                try:
                    value = d[key]
                except KeyError:
                    raise FieldNotFound(key)

                if key == 'id' and obj.backend is not None:
                    value = self.build_id(value, obj.backend)
                yield key, value

        fields_iterator = obj.iter_fields()
        d = OrderedDict(fields_iterator)
        if condition is not None and not condition.is_valid(d):
            return None
        return OrderedDict([(k, v) for k, v in iter_select_and_decorate(d)])

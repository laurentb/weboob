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


__all__ = ['SimpleFormatter']


class SimpleFormatter(object):
    @classmethod
    def format(cls, obj, selected_fields=None):
        def iter_fields(obj):
            import types
            for attribute_name in dir(obj):
                if attribute_name.startswith('_'):
                    continue
                attribute = getattr(obj, attribute_name)
                if not isinstance(attribute, types.MethodType):
                    yield attribute_name, attribute

        if hasattr(obj, 'iter_fields'):
            fields_iterator = obj.iter_fields()
        else:
            fields_iterator = iter_fields(obj)

        d = dict((k, v) for k, v in fields_iterator)

        if selected_fields is None:
            return u'\n'.join(u'%s: %s' % (k, unicode(d[k])) for k in sorted(d)) + u'\n'
        else:
            return u'\t'.join(unicode(d[k]) for k in selected_fields if d[k] is not None)

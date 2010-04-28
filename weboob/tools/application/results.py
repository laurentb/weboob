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


__all__ = ['BaseItem', 'FieldException', 'FieldsItem', 'ItemGroup', 'ObjectItem']


class FieldException(Exception):
    def __init__(self, name):
        Exception.__init__(self, 'Field "%s" does not exist.' % name)


class ItemGroup(object):
    def __init__(self, name=u'', header=None):
        self.name = name
        self._groups = []
        self._items = []
        self.header = header

    def add_item(self, item):
        self._items.append(item)

    def add_items(self, items):
        self._items.extend(items)

    def iter_items(self):
        return iter(self._items)

    def deep_iter_items(self):
        for i in self._items:
            yield i
        for g in self._groups:
            for i in g.iter_items():
                yield i

    def add_group(self, group):
        self._groups.append(group)

    def get_group(self, name):
        l = [group for group in self._groups if group.name == name]
        if l:
            return l[0]
        else:
            return None

    def get_or_create_group(self, name, group_class=None):
        if group_class is None:
            group_class = ItemGroup
        group = self.get_group(name)
        if group:
            return group
        else:
            new_group = group_class(name)
            self.add_group(new_group)
            return new_group

    def iter_groups(self):
        return iter(self._groups)

    def format(self, select=[]):
        formatted = u''
        if select:
            formatted += u'\n'.join(item.format(select) for item in self.deep_iter_items())
        else:
            if self.header:
                formatted += '%s\n' % self.header
            formatted += u'\n'.join(item.format() for item in self.iter_items())
            formatted += u'\n\n'.join(group.format() for group in self.iter_groups())
        return formatted


class BaseItem(object):
    def get(self, name):
        raise NotImplementedError()

    def format(self, select=[]):
        raise NotImplementedError()


class FieldsItem(BaseItem):
    def __init__(self, fields=[]):
        self._fields = fields

    def add_field(self, *args, **kwargs):
        if args:
            name, value = args
        elif kwargs:
            name, value = kwargs.items()[0]
        self._fields.append((name, value))

    def get(self, name):
        try:
            return [value for _name, value in self._fields if name.lower() == _name.lower()][0]
        except IndexError:
            raise FieldException(name)

    def format(self, select=[]):
        if select:
            return [value for name, value in self._fields if name in select]
        else:
            return u'; '.join(u'%s: %s' % (name, value) for name, value in self._fields)


class ObjectItem(BaseItem):
    def __init__(self, obj):
        self.obj = obj

    def get(self, name):
        try:
            return getattr(self.obj, name)
        except AttributeError:
            raise FieldException(name)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Nicolas Duhamel, Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from .base import IBaseCap

__all__ = ['ICapCollection', 'Collection', 'CollectionNotFound']


class CollectionNotFound(Exception):
    def __init__(self, split_path=None):
        if split_path is not None:
            msg = 'Collection not found: %s' % '/'.join(split_path)
        else:
            msg = 'Collection not found'
        Exception.__init__(self, msg)


class Children(object):
    """
    Dynamic property of a Collection.
    Returns a list, either by calling a function or because
    it already has the list.
    """
    def __get__(self, obj, type=None):
        if obj._children is None:
            if callable(obj._fct):
                obj._children = obj._fct(obj.id)
        return obj._children or []


class Collection(object):
    """
    Collection of objects.
    Should provide a way to be filled, either by providing the children
    right away, or a function. The function will be called once with the id
    as an argument if there were no children provided, but only on demand.
    It can be found in a list of objects, it indicantes a "folder"
    you can hop into.
    id and title should be unicode.
    """
    children = Children()

    def __init__(self, _id=None, title=None, children=None, fct=None):
        self.id = _id
        self.title = title
        # It does not make sense to have both at init
        assert not (fct is not None and children is not None)
        self._children = children
        self._fct = fct

    def __iter__(self):
        return iter(self.children)

    def __unicode__(self):
        if self.title and self.id:
            return u'%s (%s)' % (self.id, self.title)
        elif self.id:
            return u'%s' % self.id
        else:
            return u'Unknown collection'


class ICapCollection(IBaseCap):
    def _flatten_resources(self, resources, clean_only=False):
        """
        Expand all collections in a list
        If clean_only is True, do not expand collections, only remove them.
        """
        lst = list()
        for resource in resources:
            if isinstance(resource, (list, Collection)):
                if not clean_only:
                    lst.extend(self._flatten_resources(resource))
            else:
                lst.append(resource)
        return lst

    def iter_resources(self, split_path):
        """
        split_path is a list, either empty (root path) or with one or many
        components.
        """
        raise NotImplementedError()

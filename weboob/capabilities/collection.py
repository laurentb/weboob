# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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
    def __init__(self, msg=None):
        if msg is None:
            msg = 'Collection not found'
        Exception.__init__(self, msg)


class Children(object):
    def __get__(self, obj, type=None):
        if callable(obj._childrenfct):
            return obj._childrenfct(obj.id)
        else:
            return obj._children

    def __set__(self, obj, value):
        obj._childrenfct = value

class Collection(object):
    """
    _childrenfct
    _children
    appendchild
    children return iterator
    """
    children = Children()

    def __init__(self, title=None, children=None):
        self.title = title
        self._children = children if children else []
        self._childrenfct = None

    def appendchild(self, child):
        self._children.append(child)


class Ressource(object):
    pass

class ICapCollection(IBaseCap):
    def iter_resources(self, splited_path):
        raise NotImplementedError()

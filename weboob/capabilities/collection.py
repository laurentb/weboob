# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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
    
    def get_working_collection(self):
        raise NotImplementedError()

    def change_working_collection(self, splited_path):
        raise NotImplementedError()
        
    def iter_resources(self):
        raise NotImplementedError()

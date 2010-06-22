# -*- coding: utf-8 -*-

# For Python 2.5-, this will enable the simliar property mechanism as in
# Python 2.6+/3.0+. The code is based on
# http://bruynooghe.blogspot.com/2008/04/xsetter-syntax-in-python-25.html

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


import sys
import __builtin__


class property(property):
  def __init__(self, fget, *args, **kwargs):
      self.__doc__ = fget.__doc__
      super(property, self).__init__(fget, *args, **kwargs)

  def setter(self, fset):
      cls_ns = sys._getframe(1).f_locals
      for k, v in cls_ns.iteritems():
          if v == self:
              propname = k
              break
      cls_ns[propname] = property(self.fget, fset, self.fdel, self.__doc__)
      return cls_ns[propname]

  def deleter(self, fdel):
      cls_ns = sys._getframe(1).f_locals
      for k, v in cls_ns.iteritems():
          if v == self:
              propname = k
              break
      cls_ns[propname] = property(self.fget, self.fset, fdel, self.__doc__)
      return cls_ns[propname]

__builtin__.property = property

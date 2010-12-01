# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


__all__ = ['ICapDating']


class OptimizationNotFound(Exception):
    pass


class Optimization(object):
    # Configuration of optim can be made by Value*s in this dict.
    CONFIG = {}

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def is_running(self):
        raise NotImplementedError()

    def get_config(self):
        return None

    def set_config(self, params):
        raise NotImplementedError()

class ICapDating(IBaseCap):
    def init_optimizations(self):
        raise NotImplementedError()

    def add_optimization(self, name, optim):
        setattr(self, 'OPTIM_%s' % name, optim)

    def iter_optimizations(self, *optims):
        for attr_name in dir(self):
            if not attr_name.startswith('OPTIM_'):
                continue
            attr = getattr(self, attr_name)
            if attr is None:
                continue

            yield attr_name[6:], attr

    def get_optimization(self, optim):
        optim = optim.upper()
        if not hasattr(self, 'OPTIM_%s' % optim):
            raise OptimizationNotFound()

        return getattr(self, 'OPTIM_%s' % optim)

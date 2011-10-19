# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


import datetime

from .base import IBaseCap, CapBaseObject
from .contact import Contact


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


class Event(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('date', (datetime.datetime))
        self.add_field('contact', Contact)
        self.add_field('type', basestring)
        self.add_field('message', basestring)

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

    def iter_events(self):
        raise NotImplementedError()

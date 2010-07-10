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


from copy import deepcopy
from logging import error

from .config.yamlconfig import YamlConfig


class IStorage:
    def load(self, what, name, default={}):
        raise NotImplementedError()

    def save(self, what, name):
        raise NotImplementedError()

    def set(self, what, name, *args):
        raise NotImplementedError()

    def get(self, what, name, *args, **kwargs):
        raise NotImplementedError()


class StandardStorage(IStorage):
    def __init__(self, path):
        self.config = YamlConfig(path)
        self.config.load()

    def load(self, what, name, default={}):
        d = {}
        if not what in self.config.values:
            self.config.values[what] = {}
        else:
            d = self.config.values[what].get(name, {})

        self.config.values[what][name] = deepcopy(default)
        self.config.values[what][name].update(d)

    def save(self, what, name):
        self.config.save()

    def set(self, what, name, *args):
        self.config.set(what, name, *args)

    def get(self, what, name, *args, **kwargs):
        return self.config.get(what, name, *args, **kwargs)

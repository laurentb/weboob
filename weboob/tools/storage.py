# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from logging import debug

class IStorage:
    def load(self, backend, default={}):
        raise NotImplementedError()

    def save(self, backend):
        raise NotImplementedError()

    def set(self, backend, *args):
        raise NotImplementedError()

    def get(self, backend, *args, **kwargs):
        raise NotImplementedError()

try:
    from .config.yamlconfig import YamlConfig, ConfigError
except ImportError, e:
    debug('Import error for weboob.tools.config.yamlconfig: %s' % e)
else:
    class StandardStorage(IStorage):
        def __init__(self, path):
            self.config = YamlConfig(path)
            self.config.load()

        def load(self, backend, default={}):
            d = self.config.values.get(backend, {})
            self.config.values[backend] = default.copy()
            self.config.values[backend].update(d)

        def save(self, backend):
            self.config.save()

        def set(self, backend, *args):
            self.config.set(backend, *args)

        def get(self, backend, *args, **kwargs):
            return self.config.get(backend, *args, **kwargs)

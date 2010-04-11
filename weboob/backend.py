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

import re

class BackendStorage(object):
    def __init__(self, name, storage):
        self.name = name
        self.storage = storage

    def set(self, *args):
        if self.storage:
            return self.storage.set(self.name, *args)

    def get(self, *args, **kwargs):
        if self.storage:
            return self.storage.get(self.name, *args, **kwargs)
        else:
            return kwargs.get('default', None)

    def load(self, default):
        if self.storage:
            return self.storage.load(self.name, default)

    def save(self):
        if self.storage:
            return self.storage.save(self.name)

class Backend(object):
    # Module name.
    NAME = None
    # Name of the maintainer of this module.
    MAINTAINER = '<unspecifier>'
    # Email address of the maintainer.
    EMAIL = '<unspecified>'
    # Version of module (for information only).
    VERSION = '<unspecified>'
    # Description
    DESCRIPTION = '<unspecified>'
    # License of this module.
    LICENSE = '<unspecified>'
    # Configuration required for this module.  # Values must be ConfigField
    # objects.
    CONFIG = {}
    # Storage
    STORAGE = {}

    class ConfigField(object):
        def __init__(self, default=None, is_masked=False, regexp=None, description=None):
            self.default = default
            self.is_masked = is_masked
            self.regexp = regexp
            self.description = description

    class ConfigError(Exception): pass

    def __init__(self, weboob, name, config, storage):
        self.weboob = weboob
        self.name = name
        self.config = {}
        for name, field in self.CONFIG.iteritems():
            value = config.get(name, field.default)

            if value is None:
                raise Backend.ConfigError('Missing parameter "%s" (%s)' % (name, field.description))

            if field.regexp and re.match(field.regexp, str(value)):
                raise Backend.ConfigError('Value of "%s" does not match regexp "%s"' % (name, field.regexp))

            if not field.default is None:
                if isinstance(field.default, bool):
                    value = value.lower() in ('1', 'true', 'on', 'yes')
                elif isinstance(field.default, int):
                    value = int(value)
                elif isinstance(field.default, float):
                    value = float(value)
            self.config[name] = value
        self.storage = BackendStorage(self.name, storage)
        self.storage.load(self.STORAGE)

    def has_caps(self, *caps):
        for c in caps:
            if isinstance(self, c):
                return True
        return False

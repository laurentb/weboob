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




import stat
import os
import sys
try:
    from ConfigParser import RawConfigParser, DuplicateSectionError
except ImportError:
    from configparser import RawConfigParser, DuplicateSectionError
from logging import warning

__all__ = ['BackendsConfig', 'BackendAlreadyExists']


class BackendAlreadyExists(Exception):
    pass


class BackendsConfig(object):
    class WrongPermissions(Exception):
        pass

    def __init__(self, confpath):
        self.confpath = confpath
        try:
            mode = os.stat(confpath).st_mode
        except OSError:
            if not os.path.isdir(os.path.dirname(confpath)):
                os.makedirs(os.path.dirname(confpath))
            if sys.platform == 'win32':
                fptr = open(confpath, 'w')
                fptr.close()
            else:
                try:
                    os.mknod(confpath, 0o600)
                except OSError:
                    fptr = open(confpath, 'w')
                    fptr.close()
                    os.chmod(confpath, 0o600)
        else:
            if sys.platform != 'win32':
                if mode & stat.S_IRGRP or mode & stat.S_IROTH:
                    raise self.WrongPermissions(
                        u'Weboob will not start as long as config file %s is readable by group or other users.' % confpath)

    def iter_backends(self):
        config = RawConfigParser()
        config.read(self.confpath)
        changed = False
        for backend_name in config.sections():
            params = dict(config.items(backend_name))
            try:
                module_name = params.pop('_module')
            except KeyError:
                try:
                    module_name = params.pop('_backend')
                    config.set(backend_name, '_module', module_name)
                    config.remove_option(backend_name, '_backend')
                    changed = True
                except KeyError:
                    warning('Missing field "_module" for configured backend "%s"', backend_name)
                    continue
            yield backend_name, module_name, params

        if changed:
            with open(self.confpath, 'wb') as f:
                config.write(f)

    def backend_exists(self, name):
        """
        Return True if the backend exists in config.
        """
        config = RawConfigParser()
        config.read(self.confpath)
        return name in config.sections()

    def add_backend(self, backend_name, module_name, params, edit=False):
        if not backend_name:
            raise ValueError(u'Please give a name to the configured backend.')
        config = RawConfigParser()
        config.read(self.confpath)
        if not edit:
            try:
                config.add_section(backend_name)
            except DuplicateSectionError:
                raise BackendAlreadyExists(backend_name)
        config.set(backend_name, '_module', module_name)
        for key, value in params.iteritems():
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            config.set(backend_name, key, value)
        with open(self.confpath, 'wb') as f:
            config.write(f)

    def edit_backend(self, backend_name, module_name, params):
        return self.add_backend(backend_name, module_name, params, True)

    def get_backend(self, backend_name):
        config = RawConfigParser()
        config.read(self.confpath)
        if not config.has_section(backend_name):
            raise KeyError(u'Configured backend "%s" not found' % backend_name)

        items = dict(config.items(backend_name))

        try:
            module_name = items.pop('_module')
        except KeyError:
            try:
                module_name = items.pop('_backend')
                self.edit_backend(backend_name, module_name, items)
            except KeyError:
                warning('Missing field "_module" for configured backend "%s"', backend_name)
                raise KeyError(u'Configured backend "%s" not found' % backend_name)
        return module_name, items

    def remove_backend(self, backend_name):
        config = RawConfigParser()
        config.read(self.confpath)
        if not config.remove_section(backend_name):
            return False
        with open(self.confpath, 'w') as f:
            config.write(f)
        return True

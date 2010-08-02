# -*- coding: utf-8 -*-

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


from __future__ import with_statement

from ConfigParser import SafeConfigParser
import logging
import os

from .iconfig import IConfig


__all__ = ['INIConfig']


class INIConfig(IConfig):
    def __init__(self, path):
        self.path = path
        self.values = {}
        self.config = SafeConfigParser()

    def load(self, default={}):
        def load_section(section):
            sections = section.split(':')
            if len(sections) > 1:
                result = {}
                for s in sections:
                    result[s] = load_section(s)
                return result
            else:
                return {section: dict(self.config.items(section))}

        self.values = default.copy()

        if os.path.exists(self.path):
            self.config.read(self.path)
            for section in self.config.sections():
                self.values = load_section(section)
            self.values.update(self.config.items('DEFAULT'))
            logging.debug(u'Application configuration file loaded: %s.' % self.path)
        else:
            self.save()
            logging.debug(u'Application configuration file created with default values: %s. '
                          'Please customize it.' % self.path)
        return self.values

    def save(self):
        def save_section(values, root_section=None):
            for k, v in values.iteritems():
                if isinstance(v, (int, float, str, unicode)):
                    if root_section is not None and not self.config.has_section(root_section):
                        self.config.add_section(root_section)
                    self.config.set(root_section, k, unicode(v))
                elif isinstance(v, dict):
                    new_section = ':'.join((root_section, k)) if root_section else k
                    if not self.config.has_section(new_section):
                        self.config.add_section(new_section)
                    save_section(v, new_section)
        save_section(self.values)
        with open(self.path, 'w') as f:
            self.config.write(f)

    def get(self, *args, **kwargs):
        default = None
        if 'default' in kwargs:
            default = kwargs['default']

        v = self.values
        for k in args[:-1]:
            if k in v:
                v = v[k]
            else:
                return default
        try:
            return v[args[-1]]
        except KeyError:
            return default

    def set(self, *args):
        v = self.values
        for k in args[:-2]:
            if k not in v:
                v[k] = {}
            v = v[k]
        v[args[-2]] = args[-1]

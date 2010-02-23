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

from __future__ import with_statement

from ConfigParser import SafeConfigParser

class Section:
    def __init__(self, name):
        self.name = name
        self.values = {}

    def save(self, parser):
        section_created = False
        for key, value in self.values.iteritems():
            if isinstance(value, Section):
                value.save(parser)
            else:
                if not section_created:
                    parser.add_section(self.name)
                    section_created = True
                parser.set(self.name, key, value)

class Config:
    def __init__(self, path):
        self.path = path
        self.sections = {}

    def get(self, *args):
        s = None
        path = ''
        for a in args:
            if path: path += '.'
            path += a
            if not s:
                try:
                    s = self.sections[a]
                except KeyError:
                    s = self.sections[a] = Section(path)
            else:
                try:
                    s = s.values[a]
                except KeyError:
                    s = s.values[a] = Section(path)

        return s

    def load(self):
        parser = SafeConfigParser()
        parser.read(self.path)
        for section in parser.sections():
            path = section.split('.')
            s = None
            name = ''
            for part in path:
                if name: name += '.'
                name += part

                if s:
                    d = s.values
                else:
                    d = self.sections

                if not part in d:
                    d[part] = Section(name)
                s = d[part]
            options = parser.options(section)
            for o in options:
                s.values[o] = parser.get(section, o)

    def save(self):
        parser = SafeConfigParser()
        for section in self.sections.itervalues():
            section.save(parser)
        with open(self.path, 'wb') as configfile:
            parser.write(configfile)

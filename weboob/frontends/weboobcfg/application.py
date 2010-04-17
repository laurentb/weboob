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

import ConfigParser
import sys

from weboob.tools.application import ConsoleApplication

class WeboobCfg(ConsoleApplication):
    APPNAME = 'weboobcfg'

    def main(self, argv):
        return self.process_command(*argv[1:])

    def caps_included(self, modcaps, caps):
        modcaps = [x.__name__ for x in modcaps]
        for cap in caps:
            if not cap in modcaps:
                return False
        return True

    @ConsoleApplication.command('List modules')
    def command_modules(self, *caps):
        print '  Name            Capabilities          Description                             '
        print '+--------------+----------------------+----------------------------------------+'
        self.weboob.modules_loader.load()
        for name, module in self.weboob.modules_loader.modules.iteritems():
            if caps and not self.caps_included(module.iter_caps(), caps):
                continue

            first_line = True
            for cap in module.iter_caps():
                if first_line:
                    print '  %-14s %-21s %s' % (name,
                                                cap.__name__,
                                                module.get_description())
                    first_line = False
                else:
                    print '                 %s' % cap.__name__

    @ConsoleApplication.command('Display a module')
    def command_modinfo(self, name):
        try:
            module = self.weboob.modules_loader.get_or_load_module(name)
        except KeyError:
            print >>sys.stderr, 'No such module: %s' % name
            return 1

        print '.------------------------------------------------------------------------------.'
        print '| Module %-69s |' % module.get_name()
        print "+-----------------.------------------------------------------------------------'"
        print '| Version         | %s' % module.get_version()
        print '| Maintainer      | %s' % module.get_maintainer()
        print '| License         | %s' % module.get_license()
        print '| Description     | %s' % module.get_description()
        print '| Capabilities    | %s' % ', '.join([cap.__name__ for cap in module.iter_caps()])
        first = True
        for key, field in module.get_config().iteritems():
            value = field.description
            if not field.default is None:
                value += ' (default: %s)' % field.default
            if first:
                print '|                 | '
                print '| Configuration   | %s: %s' % (key, value)
                first = False
            else:
                print '|                 | %s: %s' % (key, value)
        print "'-----------------'                                                             "


    @ConsoleApplication.command('Add a backend')
    def command_add(self, type, name=None, *options):
        if not name:
            return self.command_modinfo(type)

        params = {}
        for param in options:
            try:
                key, value = param.split('=', 1)
            except ValueError:
                print >>sys.stderr, "Parameters have to be in form 'key=value'"
                return 1

            params[key] = value
        try:
            self.weboob.backends_config.add_backend(name, type, params)
        except ConfigParser.DuplicateSectionError, e:
            print >>sys.stderr, 'Error: %s (filename=%s)' % (e.message, self.weboob.backends_config.confpath)
            return 1

    @ConsoleApplication.command('List backends')
    def command_list(self):
        print '  Name           Type           Params                                          '
        print '+--------------+--------------+------------------------------------------------+'
        for name, _type, params in self.weboob.backends_config.iter_backends():
            print '  %-14s %-14s %-47s' % (name,
                                           _type,
                                           ', '.join(['%s=%s' % (key, value) for key, value in params.iteritems()]))

    @ConsoleApplication.command('Remove a backend')
    def command_remove(self, name):
        try:
            self.weboob.backends_config.remove_backend(name)
        except ConfigParser.NoSectionError:
            print >>sys.stderr, "Backend '%s' does not exist" % name
            return 1

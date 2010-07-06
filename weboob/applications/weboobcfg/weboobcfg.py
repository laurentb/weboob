# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Christophe Benz
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

import ConfigParser
import logging
import os
import subprocess
import re

from weboob.tools.application import ConsoleApplication


__all__ = ['WeboobCfg']


class WeboobCfg(ConsoleApplication):
    APPNAME = 'weboobcfg'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

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
                    print '  %-14s %-21s %s' % (name, cap.__name__, module.get_description())
                    first_line = False
                else:
                    print '                 %s' % cap.__name__

    @ConsoleApplication.command('List applications')
    def command_applications(self, *caps):
        applications = set()
        import weboob.applications
        for path in weboob.applications.__path__:
            regexp = re.compile('^%s/([\w\d_]+)$' % path)
            for root, dirs, files in os.walk(path):
                m = regexp.match(root)
                if m and '__init__.py' in files:
                    applications.add(m.group(1))
        print ' '.join(sorted(applications)).encode('utf-8')

    @ConsoleApplication.command('Display a module')
    def command_modinfo(self, name):
        try:
            module = self.weboob.modules_loader.get_or_load_module(name)
        except KeyError:
            logging.error('No such module: %s' % name)
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


    @ConsoleApplication.command('Add a configured backend')
    def command_add(self, name, *options):
        self.weboob.modules_loader.load()
        if name not in [module_name for module_name, module in self.weboob.modules_loader.modules.iteritems()]:
            logging.error(u'Backend "%s" does not exist.' % name)
            return 1

        params = {}
        # set backend params from command-line arguments
        for option in options:
            try:
                key, value = option.split('=', 1)
            except ValueError:
                logging.error(u'Parameters have to be formatted "key=value"')
                return 1
            params[key] = value
        # ask for params non-specified on command-line arguments
        module = self.weboob.modules_loader.get_or_load_module(name)
        asked_config = False
        for key, value in module.get_config().iteritems():
            if not asked_config:
                asked_config = True
                print u'Configuration of backend'
                print u'------------------------'
            if key not in params:
                params[key] = self.ask(' [%s] %s' % (key, value.description),
                                       default=value.default,
                                       masked=value.is_masked,
                                       regexp=value.regexp)
            else:
                print u' [%s] %s: %s' % (key, value.description, '(masked)' if value.is_masked else params[key])
        if asked_config:
            print u'------------------------'

        try:
            self.weboob.backends_config.add_backend(name, name, params)
            print u'Backend "%s" successfully added to file "%s".\n'\
                    'Please check configuration parameters values with "weboobcfg edit".' % (
                        name, self.weboob.backends_config.confpath)
        except ConfigParser.DuplicateSectionError:
            print u'Backend "%s" is already configured in file "%s"' % (name, self.weboob.backends_config.confpath)
            response = raw_input(u'Add new instance of "%s" backend? [yN] ' % name)
            if response.lower() == 'y':
                while True:
                    new_name = raw_input(u'Please give new instance name (could be "%s_1"): ' % name)
                    if not new_name:
                        continue
                    try:
                        self.weboob.backends_config.add_backend(new_name, name, params)
                        print u'Backend "%s" successfully added to file "%s".\n'\
                                'Please check configuration parameters values with "weboobcfg edit".' % (
                                    name, self.weboob.backends_config.confpath)
                        break
                    except ConfigParser.DuplicateSectionError:
                        print u'Instance "%s" already exists for backend "%s".' % (new_name, name)

    @ConsoleApplication.command('List backends')
    def command_list(self):
        print '  Instance Name   Name           Params                                          '
        print '+---------------+--------------+------------------------------------------------+'
        for instance_name, name, params in self.weboob.backends_config.iter_backends():
            print '  %-15s %-14s %-47s' % (instance_name, name, ', '.join('%s=%s' % (key, value) for key, value in params.iteritems()))

    @ConsoleApplication.command('Remove a backend')
    def command_remove(self, instance_name):
        try:
            self.weboob.backends_config.remove_backend(instance_name)
        except ConfigParser.NoSectionError:
            logging.error("Backend '%s' does not exist" % instance_name)
            return 1

    @ConsoleApplication.command('Edit configuration file')
    def command_edit(self):
        subprocess.call([os.environ.get('EDITOR', 'vi'), self.weboob.backends_config.confpath])

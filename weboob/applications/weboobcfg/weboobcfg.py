# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Christophe Benz
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


import os
import sys
import re
from copy import copy

from weboob.capabilities.account import ICapAccount
from weboob.core.modules import ModuleLoadError
from weboob.tools.application.repl import ReplApplication
from weboob.tools.ordereddict import OrderedDict


__all__ = ['WeboobCfg']


class WeboobCfg(ReplApplication):
    APPNAME = 'weboob-config'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz, Romain Bignon'
    DESCRIPTION = "Weboob-Config is a console application to add/edit/remove backends, " \
                  "and to register new website accounts."
    COMMANDS_FORMATTERS = {'backends':    'table',
                           'list':        'table',
                           }
    DISABLE_REPL = True

    weboob_commands = copy(ReplApplication.weboob_commands)
    weboob_commands.remove('backends')

    def load_default_backends(self):
        pass

    def do_add(self, line):
        """
        add NAME [OPTIONS ...]

        Add a configured backend.
        """
        if not line:
            print >>sys.stderr, 'You must specify a backend name. Hint: use the "backends" command.'
            return 2
        name, options = self.parse_command_args(line, 2, 1)
        if options:
            options = options.split(' ')
        else:
            options = ()

        params = {}
        # set backend params from command-line arguments
        for option in options:
            try:
                key, value = option.split('=', 1)
            except ValueError:
                print >>sys.stderr, 'Parameters have to be formatted "key=value"'
                return 2
            params[key] = value

        self.add_backend(name, params)

    def do_register(self, line):
        """
        register NAME

        Register a new account on a backend.
        """
        self.register_backend(line)

    def do_confirm(self, backend_name):
        """
        confirm BACKEND

        For a backend which support CapAccount, parse a confirmation mail
        after using the 'register' command to automatically confirm the
        subscribe.

        It takes mail from stdin. Use it with postfix for example.
        """
        # Do not use the ReplApplication.load_backends() method because we
        # don't want to prompt user to create backend.
        self.weboob.load_backends(names=[backend_name])
        try:
            backend = self.weboob.get_backend(backend_name)
        except KeyError:
            print >>sys.stderr, 'Error: backend "%s" not found.' % backend_name
            return 1

        if not backend.has_caps(ICapAccount):
            print >>sys.stderr, 'Error: backend "%s" does not support accounts management' % backend_name
            return 1

        mail = sys.stdin.read()
        if not backend.confirm_account(mail):
            print >>sys.stderr, 'Error: Unable to confirm account creation'
            return 1
        return 0

    def do_list(self, line):
        """
        list [CAPS ..]

        Show configured backends.
        """
        caps = line.split()
        for instance_name, name, params in sorted(self.weboob.backends_config.iter_backends()):
            backend = self.weboob.modules_loader.get_or_load_module(name)
            if caps and not self.caps_included(backend.iter_caps(), caps):
                continue
            row = OrderedDict([('Instance name', instance_name),
                               ('Backend', name),
                               ('Configuration', ', '.join(
                                   '%s=%s' % (key, ('*****' if key in backend.config and backend.config[key].masked \
                                                    else value)) \
                                   for key, value in params.iteritems())),
                               ])
            self.format(row)
        self.flush()

    def do_remove(self, instance_name):
        """
        remove NAME

        Remove a configured backend.
        """
        if not self.weboob.backends_config.remove_backend(instance_name):
            print >>sys.stderr, 'Backend instance "%s" does not exist' % instance_name
            return 1

    def do_edit(self, line):
        """
        edit NAME

        Edit a backend
        """
        try:
            self.edit_backend(line)
        except KeyError:
            print >>sys.stderr, 'Error: backend "%s" not found' % line
            return 1

    def do_backends(self, line):
        """
        backends [CAPS ...]

        Show available backends.
        """
        caps = line.split()
        self.weboob.modules_loader.load_all()
        for name, backend in sorted(self.weboob.modules_loader.loaded.iteritems()):
            if caps and not self.caps_included(backend.iter_caps(), caps):
                continue
            row = OrderedDict([('Name', name),
                               ('Capabilities', ', '.join(cap.__name__ for cap in backend.iter_caps())),
                               ('Description', backend.description),
                               ])
            self.format(row)
        self.flush()

    def do_info(self, line):
        """
        info NAME

        Display information about a backend.
        """
        if not line:
            print >>sys.stderr, 'You must specify a backend name. Hint: use the "backends" command.'
            return 2

        try:
            backend = self.weboob.modules_loader.get_or_load_module(line)
        except ModuleLoadError:
            backend = None

        if not backend:
            print >>sys.stderr, 'Backend "%s" does not exist.' % line
            return 1

        print '.------------------------------------------------------------------------------.'
        print '| Backend %-68s |' % backend.name
        print "+-----------------.------------------------------------------------------------'"
        print '| Version         | %s' % backend.version
        print '| Maintainer      | %s' % backend.maintainer
        print '| License         | %s' % backend.license
        print '| Description     | %s' % backend.description
        print '| Capabilities    | %s' % ', '.join([cap.__name__ for cap in backend.iter_caps()])
        first = True
        for key, field in backend.config.iteritems():
            value = field.label
            if not field.default is None:
                value += ' (default: %s)' % field.default
            if first:
                print '|                 | '
                print '| Configuration   | %s: %s' % (key, value)
                first = False
            else:
                print '|                 | %s: %s' % (key, value)
        print "'-----------------'"

    def do_applications(self, line):
        """
        applications

        Show applications.
        """
        applications = set()
        import weboob.applications
        for path in weboob.applications.__path__:
            regexp = re.compile('^%s/([\w\d_]+)$' % path)
            for root, dirs, files in os.walk(path):
                m = regexp.match(root)
                if m and '__init__.py' in files:
                    applications.add(m.group(1))
        print ' '.join(sorted(applications)).encode('utf-8')

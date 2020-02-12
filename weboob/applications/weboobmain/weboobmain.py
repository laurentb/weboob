#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ft=python et softtabstop=4 cinoptions=4 shiftwidth=4 ts=4 ai


# Copyright(C) 2009-2017  Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import print_function

import inspect
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime, timedelta

import weboob.applications

from weboob.tools.application.console import ConsoleApplication

try:
    from weboob.tools.application.qt5 import QtApplication
except ImportError:
    class QtApplication(object):
        pass


__all__ = ['WeboobMain']


class WeboobMain(ConsoleApplication):
    APPNAME = 'weboob'
    VERSION = '2.0'
    COPYRIGHT = 'Copyright(C) 2010-YEAR The Weboob Team'
    DESCRIPTION = "This is a console script to launch weboob applications,"
    SHORT_DESCRIPTION = "launch weboob applications"

    UPDATE_DAYS_DELAY = 20

    def main(self):
        interactive = sys.stdout.isatty()
        if interactive:
            self.update()

        capApplicationDict = self.init_CapApplicationDict()

        if len(sys.argv) >= 2:
            try:
                cmd = getattr(self, 'cmd_%s' % sys.argv[1])
            except AttributeError:
                pass
            else:
                cmd()
                return

            cap = sys.argv.pop(1)
            if cap not in capApplicationDict:
                if interactive:
                    print('Unknown capability, please choose one in the following list')
                    cap = self.choose_capability(capApplicationDict)
                else:
                    cap = None

        else:
            if interactive:
                cap = self.choose_capability(capApplicationDict)
            else:
                cap = None

        def appsortkey(app):
            if issubclass(app, QtApplication):
                return '1' + app.APPNAME
            else:
                return '0' + app.APPNAME

        if cap:
            applications = capApplicationDict[cap]
            applications = sorted(set(applications), key=appsortkey)
            application = applications[0] if len(applications) == 1 else self.choose_application(applications)

            application.run()
        else:
            print('Please provide a capability.')

    def cmd_update(self):
        self.weboob.update()

    def update(self):
        for repository in self.weboob.repositories.repositories:
            update_date = datetime.strptime(str(repository.update), '%Y%m%d%H%M')
            if (datetime.now() - timedelta(days=self.UPDATE_DAYS_DELAY)) > update_date:
                update = self.ask('The repositories have not been updated for %s days, do you want to update them ? (y/n)'
                                  % self.UPDATE_DAYS_DELAY,
                                  default='n')
                if update.upper() == 'Y':
                    self.weboob.repositories.update()
                break

    def choose_application(self, applications):
        application = None
        while not application:
            for app in applications:
                print('  %s%2d)%s %s: %s' % (self.BOLD,
                                             applications.index(app) + 1,
                                             self.NC,
                                             app.APPNAME,
                                             app.DESCRIPTION))
            r = self.ask('  Select an application', regexp='(\d+|)', default='')
            if not r.isdigit():
                continue
            r = int(r)
            if r <= 0 or r > len(applications):
                continue
            application = applications[r - 1]
        return application

    def choose_capability(self, capApplicationDict):
        cap = None
        caps = list(capApplicationDict.keys())
        while cap not in caps:
            for n, _cap in enumerate(caps):
                print('  %s%2d)%s %s' % (self.BOLD, n + 1, self.NC, _cap))
            r = self.ask('  Select a capability', regexp='(\d+|)', default='')
            if not r.isdigit():
                continue
            r = int(r)
            if r <= 0 or r > len(caps):
                continue
            cap = caps[r - 1]
        return cap

    def init_CapApplicationDict(self):
        capApplicationDict = {}
        for path in weboob.applications.__path__:
            regexp = re.compile('^%s/([\w\d_]+)$' % path)
            for root, dirs, files in os.walk(path):
                m = regexp.match(root)
                if not (m and '__init__.py' in files):
                    continue

                application = self.get_applicaction_from_filename(m.group(1))
                if not application:
                    continue

                capabilities = self.get_application_capabilities(application)
                if not capabilities:
                    continue

                for capability in capabilities:
                    if capability in capApplicationDict:
                        capApplicationDict[capability].append(application)
                    else:
                        capApplicationDict[capability] = [application]

        return OrderedDict([(k, v) for k, v in sorted(capApplicationDict.items())])

    def get_application_capabilities(self, application):
        if hasattr(application, 'CAPS') and application.CAPS:
            _capabilities = list(application.CAPS) if isinstance(application.CAPS, tuple) else [application.CAPS]
            return [os.path.splitext(os.path.basename(inspect.getfile(x)))[0] for x in _capabilities]

    def get_applicaction_from_filename(self, name):
        module = 'weboob.applications.%s.%s' % (name, name)
        try:
            _module = __import__(module, fromlist=['*'])
        except ImportError:
            return

        _application = [x for x in dir(_module) if x.lower() == name]
        if _application:
            return getattr(_module, _application[0])

    @classmethod
    def run(cls):
        try:
            cls().main()
        except KeyboardInterrupt:
            print('')

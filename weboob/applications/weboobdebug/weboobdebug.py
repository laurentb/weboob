# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


import sys

from weboob.tools.application.repl import ReplApplication


class WeboobDebug(ReplApplication):
    APPNAME = 'weboobdebug'
    VERSION = '0.8.1'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz'
    DESCRIPTION = "Weboob-Debug is a console application to debug backends."

    def load_default_backends(self):
        pass

    def do_shell(self, backend_name):
        """
        shell BACKEND

        Debug a backend.
        """
        try:
            backend = self.weboob.load_backends(names=[backend_name])[backend_name]
        except KeyError:
            print >>sys.stderr, u'Unable to load backend "%s"' % backend_name
            return 1
        browser = backend.browser
        from IPython.Shell import IPShellEmbed
        shell = IPShellEmbed(argv=[])
        locs = dict(backend=backend, browser=browser, application=self, weboob=self.weboob)
        banner = 'Weboob debug shell\nBackend "%s" loaded.\nAvailable variables: %s' % (backend_name, locs)
        shell.set_banner(shell.IP.BANNER + '\n\n' + banner)
        shell(local_ns=locs, global_ns={})

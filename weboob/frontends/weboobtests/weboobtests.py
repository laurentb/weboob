# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

from nose import run

from weboob.tools.application import ConsoleApplication

__all__ = ['WeboobTests']


class WeboobTests(ConsoleApplication):
    APPNAME = 'weboobtests'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def main(self, argv):
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Run tests')
    def command_run(self):
        self.load_modules()
        self.load_backends()

        suite = []
        for backend in self.weboob.iter_backends():
            t = backend.get_test()
            if t:
                suite.append(t)

        return run(suite=suite)

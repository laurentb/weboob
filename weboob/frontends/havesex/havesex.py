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


from __future__ import with_statement

import sys

import weboob
from weboob.tools.application import PromptApplication
from weboob.capabilities.dating import ICapDating, OptimizationNotFound


__all__ = ['HaveSex']


class HaveSex(PromptApplication):
    APPNAME = 'havesex'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    STORAGE_FILENAME = 'dating.storage'
    CONFIG = {'optimizations': ''}

    def main(self, argv):
        self.load_config()
        self.load_backends(ICapDating, storage=self.create_storage(self.STORAGE_FILENAME))

        self.weboob.do('init_optimizations').wait()

        self.optims('Starting', 'start_optimization', self.config.get('optimizations').split(' '))

        return self.loop()

    @PromptApplication.command("exit program")
    def command_exit(self):
        print 'Returning in real-life...'
        self.weboob.want_stop()

    @PromptApplication.command("show a profile")
    def command_profile(self, id):
        _id, backend_name = self.parse_id(id)

        found = 0
        for backend, profile in self.weboob.do_backends(backend_name, 'get_profile', _id):
            if profile:
                print profile.get_profile_text()
                found = 1

        if not found:
            print >>sys.stderr, 'Profile not found'

        return True

    def service(self, action, function, *params):
        sys.stdout.write('%s:' % action)
        for backend, result in self.weboob.do(function, *params):
            if result:
                sys.stdout.write(' ' + backend.name)
                sys.stdout.flush()
        sys.stdout.write('.\n')

    def optims(self, action, function, optims):
        for optim in optims:
            try:
                self.service('Starting %s' % optim, 'start_optimization', optim)
            except weboob.CallErrors, errors:
                for backend, error, backtrace in errors:
                    if isinstance(error, OptimizationNotFound):
                        print 'Optimization "%s" not found' % optim

    @PromptApplication.command("start optimizations")
    def command_start(self, *optims):
        self.optims('Starting', 'start_optimization', optims)

    @PromptApplication.command("stop optimizations")
    def command_stop(self, *optims):
        self.optims('Stopping', 'stop_optimization', optims)

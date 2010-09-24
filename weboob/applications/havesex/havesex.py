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

import logging
import sys

import weboob
from weboob.tools.application.repl import ReplApplication
from weboob.capabilities.dating import ICapDating, OptimizationNotFound


__all__ = ['HaveSex']


class HaveSex(ReplApplication):
    APPNAME = 'havesex'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    STORAGE_FILENAME = 'dating.storage'
    CONFIG = {'optimizations': ''}

    def load_default_backends(self):
        self.load_backends(ICapDating, storage=self.create_storage(self.STORAGE_FILENAME))

    def main(self, argv):
        self.load_config()

        self.do('init_optimizations').wait()

        optimizations = self.config.get('optimizations')
        if optimizations:
            optimizations_list = optimizations.strip().split(' ')
            if optimizations_list:
                self.optims('Starting', 'start_optimization', optimizations_list)

        return ReplApplication.main(self, argv)

    def do_profile(self, id):
        """
        profile ID

        Display a profile
        """
        _id, backend_name = self.parse_id(id)

        def print_node(node, level=1):
            if node.flags & node.SECTION:
                print '\t' * level + node.label
                for sub in node.value:
                    print_node(sub, level+1)
            else:
                if isinstance(node.value, (tuple,list)):
                    value = ','.join([unicode(v) for v in node.value])
                else:
                    value = node.value
                print '\t' * level + '%-20s %s' % (node.label + ':', value)

        found = 0
        for backend, contact in self.do('get_contact', _id, backends=backend_name):
            if contact:
                print 'Nickname:', contact.name
                if contact.status & contact.STATUS_ONLINE:
                    s = 'online'
                elif contact.status & contact.STATUS_OFFLINE:
                    s = 'offline'
                elif contact.status & contact.STATUS_AWAY:
                    s = 'away'
                else:
                    s = 'unknown'
                print 'Status: %s (%s)' % (s, contact.status_msg)
                print 'Photos:'
                for name, photo in contact.photos.iteritems():
                    print '\t%s' % photo
                print 'Profile:'
                for head in contact.profile:
                    print_node(head)
                print 'Description:'
                print '\n'.join(['\t%s' % s for s in contact.summary.split('\n')])
                found = 1

        if not found:
            logging.error(u'Profile not found')

        return True

    def service(self, action, function, *params):
        sys.stdout.write('%s:' % action)
        for backend, result in self.do(function, *params):
            if result:
                sys.stdout.write(' ' + backend.name)
                sys.stdout.flush()
        sys.stdout.write('.\n')

    def optims(self, action, function, optims):
        for optim in optims:
            try:
                self.service('Starting "%s"' % optim, 'start_optimization', optim)
            except weboob.core.CallErrors, errors:
                for backend, error, backtrace in errors:
                    if isinstance(error, OptimizationNotFound):
                        logging.error(u'Optimization "%s" not found' % optim)

    def do_start(self, *optims):
        """
        start OPTIMIZATION [OPTIMIZATION [...]]

        Start optimization services.
        """
        self.optims('Starting', 'start_optimization', optims)

    def command_stop(self, *optims):
        """
        stop OPTIMIZATION [OPTIMIZATION [...]]

        Stop optimization services.
        """
        self.optims('Stopping', 'stop_optimization', optims)

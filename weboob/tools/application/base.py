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

import sys, os
import logging
from optparse import OptionParser

from weboob import Weboob

class BaseApplication(object):
    # Application name
    APPNAME = ''
    # Default configuration
    CONFIG = {}
    # Configuration directory
    CONFDIR = os.path.join(os.path.expanduser('~'), '.weboob')

    def __init__(self):
        self.weboob = self.create_weboob()
        self.config = None

    def create_weboob(self):
        return Weboob(self.APPNAME)

    def create_storage(self, path=None, klass=None):
        """
        Create a storage object.

        @param path [str]  an optional specific path.
        @param klass [IStorage]  what klass to instance.
        @return  a IStorage object
        """
        if klass is None:
            # load StandardStorage only here because some applications don't
            # want # to depend on yaml and do not use this function
            from weboob.tools.storage import StandardStorage
            klass = StandardStorage

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME + '.storage')
        elif not path.startswith('/'):
            path = os.path.join(self.CONFDIR, path)

        return klass(path)

    def load_config(self, path=None, klass=None):
        """
        Load a configuration file and get his object.

        @param path [str]  an optional specific path.
        @param klass [IConfig]  what klass to instance.
        @return  a IConfig object
        """
        if klass is None:
            # load Config only here because some applications don't want
            # to depend on yaml and do not use this function
            from weboob.tools.config.yamlconfig import YamlConfig
            klass = YamlConfig

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME)
        elif not path.startswith('/'):
            path = os.path.join(self.CONFDIR, path)

        self.config = klass(path)
        self.config.load(self.CONFIG)

    def main(self, argv):
        """ Main function """
        raise NotImplementedError()

    @classmethod
    def run(klass):
        app = klass()
        parser = OptionParser('Usage: %prog [options (-h for help)] URL...') 
        parser.add_option('-d', '--debug', action='store_true', help='display debug messages') 
        parser.add_option('-q', '--quiet', action='store_true', help='display only error messages') 
        parser.add_option('-v', '--verbose', action='store_true', help='display info messages') 
        options, args = parser.parse_args(sys.argv)
        if options.debug:
            level=logging.DEBUG
        elif options.verbose:
            level = logging.INFO
        elif options.quiet:
            level = logging.ERROR
        else:
            level = logging.WARNING
        log_format = '%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d %(message)s'
        logging.basicConfig(stream=sys.stdout, level=level, format=log_format)
        sys.exit(app.main(args))

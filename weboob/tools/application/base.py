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


import sys, os
import logging
import optparse
from optparse import OptionGroup, OptionParser

from weboob import Weboob
from weboob.tools.config.iconfig import ConfigError


__all__ = ['BaseApplication', 'ConfigError']


class BaseApplication(object):
    # Application name
    APPNAME = ''
    # Default configuration
    CONFIG = {}
    # Configuration directory
    CONFDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    # Synopsis
    SYNOPSIS = 'Usage: %prog [options (-h for help)] ...'
    # Version
    VERSION = None
    # Copyright
    COPYRIGHT = None

    def __init__(self, option_parser=None):
        self.weboob = self.create_weboob()
        self.config = None
        if option_parser is None:
            self._parser = OptionParser(self.SYNOPSIS, version=self._get_optparse_version())
        else:
            self._parser = option_parser
        self._parser.add_option('-b', '--backends', help='what backend(s) to enable (comma separated)')
        logging_options = OptionGroup(self._parser, 'Logging Options')
        logging_options.add_option('-d', '--debug', action='store_true', help='display debug messages')
        logging_options.add_option('-q', '--quiet', action='store_true', help='display only error messages')
        logging_options.add_option('-v', '--verbose', action='store_true', help='display info messages')
        self._parser.add_option_group(logging_options)
        self._parser.add_option('--shell-completion', action='store_true', help=optparse.SUPPRESS_HELP)

    def create_weboob(self):
        return Weboob()

    def create_storage(self, path=None, klass=None):
        """
        Create a storage object.

        @param path [str]  an optional specific path.
        @param klass [IStorage]  what klass to instance.
        @return  a IStorage object
        """
        if klass is None:
            # load StandardStorage only here because some applications don't
            # want to depend on yaml and do not use this function
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
            # from weboob.tools.config.yamlconfig import YamlConfig
            # klass = YamlConfig
            from weboob.tools.config.iniconfig import INIConfig
            klass = INIConfig

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME)
        elif not path.startswith('/'):
            path = os.path.join(self.CONFDIR, path)

        self.config = klass(path)
        self.config.load(self.CONFIG)

    def main(self, argv):
        """ Main function """
        raise NotImplementedError()

    def load_backends(self, caps=None, names=None, *args, **kwargs):
        if names is None:
            names = self._enabled_backends
        return self.weboob.load_backends(caps, names, *args, **kwargs)

    def load_modules(self, caps=None, names=None, *args, **kwargs):
        if names is None:
            names = self._enabled_backends
        return self.weboob.load_modules(caps, names, *args, **kwargs)

    def _get_completions(self):
        """
        Overload this method in subclasses if you want to enrich shell completion.
        @return  a set object
        """
        return set()

    def _get_optparse_version(self):
        version = None
        if self.VERSION:
            if self.COPYRIGHT:
                version = '%s v%s (%s)' % (self.APPNAME, self.VERSION, self.COPYRIGHT)
            else:
                version = '%s v%s' % (self.APPNAME, self.VERSION)
        return version

    def _handle_app_options(self):
        """
        Overload this method in subclasses if you want to handle options defined in subclass constructor.
        """
        pass

    @classmethod
    def run(klass, args=None):
        if args is None:
            args = [(sys.stdin.encoding and arg.decode(sys.stdin.encoding) or arg) for arg in sys.argv]
        app = klass()
        app.options, args = app._parser.parse_args(args)

        if app.options.shell_completion:
            items = set()
            for option in app._parser.option_list:
                if not option.help is optparse.SUPPRESS_HELP:
                    items.update(str(option).split('/'))
            items.update(app._get_completions())
            print ' '.join(items)
            sys.exit(0)

        if app.options.debug:
            level=logging.DEBUG
        elif app.options.verbose:
            level = logging.INFO
        elif app.options.quiet:
            level = logging.ERROR
        else:
            level = logging.WARNING
        log_format = '%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(funcName)s %(message)s'
        logging.basicConfig(stream=sys.stdout, level=level, format=log_format)
        app._enabled_backends = app.options.backends.split(',') if app.options.backends else None

        app._handle_app_options()

        try:
            sys.exit(app.main(args))
        except KeyboardInterrupt:
            print 'Program killed by SIGINT'
        except ConfigError, e:
            print 'Configuration error: %s' % e
            sys.exit(1)

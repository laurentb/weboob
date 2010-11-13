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


import sys, os
import logging
import optparse
from optparse import OptionGroup, OptionParser

from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.core import Weboob, CallErrors
from weboob.tools.config.iconfig import ConfigError
from weboob.tools.backend import ObjectNotAvailable
from weboob.tools.log import createColoredFormatter, getLogger


__all__ = ['BackendNotFound', 'BaseApplication']


class BackendNotFound(Exception):
    pass


class ApplicationStorage(object):
    def __init__(self, name, storage):
        self.name = name
        self.storage = storage

    def set(self, *args):
        if self.storage:
            return self.storage.set('applications', self.name, *args)

    def delete(self, *args):
        if self.storage:
            return self.storage.delete('applications', self.name, *args)

    def get(self, *args, **kwargs):
        if self.storage:
            return self.storage.get('applications', self.name, *args, **kwargs)
        else:
            return kwargs.get('default', None)

    def load(self, default):
        if self.storage:
            return self.storage.load('applications', self.name, default)

    def save(self):
        if self.storage:
            return self.storage.save('applications', self.name)

class BaseApplication(object):
    """
    Base application.

    This class can be herited to have some common code within weboob
    applications.
    """

    # ------ Class attributes --------------------------------------

    # Application name
    APPNAME = ''
    # Configuration and work directory (default: ~/.weboob/)
    CONFDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    # Default configuration dict (can only contain key/values)
    CONFIG = {}
    # Default storage tree
    STORAGE = {}
    # Synopsis
    SYNOPSIS =  'Usage: %prog [-h] [-dqv] [-b backends] ...\n'
    SYNOPSIS += '       %prog [--help] [--version]'
    # Description
    DESCRIPTION = None
    # Version
    VERSION = None
    # Copyright
    COPYRIGHT = None

    # ------ Abstract methods --------------------------------------
    def create_weboob(self):
        return Weboob()

    def _get_completions(self):
        """
        Overload this method in subclasses if you want to enrich shell completion.
        @return  a set object
        """
        return set()

    def _handle_options(self):
        """
        Overload this method in application type subclass
        if you want to handle options defined in subclass constructor.
        """
        pass

    def add_application_options(self, group):
        """
        Overload this method if your application needs extra options.

        These options will be displayed in an option group.
        """
        pass

    def handle_application_options(self):
        """
        Overload this method in your application if you want to handle options defined in add_application_options.
        """
        pass

    # ------ BaseApplication methods -------------------------------

    def __init__(self, option_parser=None):
        self.logger = getLogger(self.APPNAME)
        self.weboob = self.create_weboob()
        self.config = None
        self.options = None
        if option_parser is None:
            self._parser = OptionParser(self.SYNOPSIS, version=self._get_optparse_version())
        else:
            self._parser = option_parser
        if self.DESCRIPTION:
            self._parser.description = self.DESCRIPTION
        app_options = OptionGroup(self._parser, '%s Options' % self.APPNAME.capitalize())
        self.add_application_options(app_options)
        if len(app_options.option_list) > 0:
            self._parser.add_option_group(app_options)
        self._parser.add_option('-b', '--backends', help='what backend(s) to enable (comma separated)')
        logging_options = OptionGroup(self._parser, 'Logging Options')
        logging_options.add_option('-d', '--debug', action='store_true', help='display debug messages')
        logging_options.add_option('-q', '--quiet', action='store_true', help='display only error messages')
        logging_options.add_option('-v', '--verbose', action='store_true', help='display info messages')
        logging_options.add_option('--logging-file', action='store', type='string', dest='logging_file', help='file to save logs')
        logging_options.add_option('-a', '--save-responses', action='store_true', help='save every response')
        self._parser.add_option_group(logging_options)
        self._parser.add_option('--shell-completion', action='store_true', help=optparse.SUPPRESS_HELP)

    def deinit(self):
        self.weboob.want_stop()
        self.weboob.deinit()

    def create_storage(self, path=None, klass=None, localonly=False):
        """
        Create a storage object.

        @param path [str]  an optional specific path.
        @param klass [IStorage]  what klass to instance.
        @param localonly [bool]  if True, do not set it on the Weboob object.
        @return  a IStorage object
        """
        if klass is None:
            from weboob.tools.storage import StandardStorage
            klass = StandardStorage

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME + '.storage')
        elif not path.startswith('/'):
            path = os.path.join(self.CONFDIR, path)

        storage = klass(path)
        self.storage = ApplicationStorage(self.APPNAME, storage)
        self.storage.load(self.STORAGE)

        if not localonly:
            self.weboob.storage = storage

        return storage

    def load_config(self, path=None, klass=None):
        """
        Load a configuration file and get his object.

        @param path [str]  an optional specific path.
        @param klass [IConfig]  what klass to instance.
        @return  a IConfig object
        """
        if klass is None:
            from weboob.tools.config.iniconfig import INIConfig
            klass = INIConfig

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME)
        elif not path.startswith('/'):
            path = os.path.join(self.CONFDIR, path)

        self.config = klass(path)
        self.config.load(self.CONFIG)

    def main(self, argv):
        """
        Main method

        Called by run
        """
        raise NotImplementedError()

    def load_backends(self, caps=None, names=None, *args, **kwargs):
        if names is None and self.options.backends:
            names = self.options.backends.split(',')
        loaded = self.weboob.load_backends(caps, names, *args, **kwargs)
        if not loaded:
            logging.warning(u'No backend loaded')
        return loaded

    def _get_optparse_version(self):
        version = None
        if self.VERSION:
            if self.COPYRIGHT:
                version = '%s v%s %s' % (self.APPNAME, self.VERSION, self.COPYRIGHT)
            else:
                version = '%s v%s' % (self.APPNAME, self.VERSION)
        return version

    def _do_complete_obj(self, backend, fields, obj):
        if fields:
            try:
                backend.fillobj(obj, fields)
            except ObjectNotAvailable, e:
                logging.warning(u'Could not retrieve required fields (%s): %s' % (','.join(fields), e))
                for field in fields:
                    if getattr(obj, field) is NotLoaded:
                        setattr(obj, field, NotAvailable)
        return obj

    def _do_complete_iter(self, backend, count, fields, res):
        for i, sub in enumerate(res):
            if count and i == count:
                break
            sub = self._do_complete_obj(backend, fields, sub)
            yield sub

    def _do_complete(self, backend, count, selected_fields, function, *args, **kwargs):
        assert count is None or count > 0
        if callable(function):
            res = function(backend, *args, **kwargs)
        else:
            res = getattr(backend, function)(*args, **kwargs)

        if hasattr(res, '__iter__'):
            return self._do_complete_iter(backend, count, selected_fields, res)
        else:
            return self._do_complete_obj(backend, selected_fields, res)

    def bcall_error_handler(self, backend, error, backtrace):
        """
        Handler for an exception inside the CallErrors exception.

        This method can be overrided to support more exceptions types.
        """
        print >>sys.stderr, u'Error(%s): %s' % (backend.name, error)
        if logging.root.level == logging.DEBUG:
            print >>sys.stderr, backtrace

    def bcall_errors_handler(self, errors):
        """
        Handler for the CallErrors exception.
        """
        for backend, error, backtrace in errors.errors:
            self.bcall_error_handler(backend, error, backtrace)
        if logging.root.level != logging.DEBUG:
            print >>sys.stderr, 'Use --debug option to print backtraces.'

    def parse_args(self, args):
        self.options, args = self._parser.parse_args(args)

        if self.options.shell_completion:
            items = set()
            for option in self._parser.option_list:
                if not option.help is optparse.SUPPRESS_HELP:
                    items.update(str(option).split('/'))
            items.update(self._get_completions())
            print ' '.join(items)
            sys.exit(0)

        if self.options.save_responses:
            from weboob.tools.browser import BaseBrowser
            BaseBrowser.SAVE_RESPONSES = True

        for handler in logging.root.handlers:
            logging.root.removeHandler(handler)

        if self.options.debug:
            level = logging.DEBUG
        elif self.options.verbose:
            level = logging.INFO
        elif self.options.quiet:
            level = logging.ERROR
        else:
            level = logging.WARNING

        logging.root.setLevel(level)

        # file logger
        if self.options.logging_file:
            try:
                stream = open(self.options.logging_file, 'w')
            except IOError, e:
                self.logger.error('Unable to create the logging file: %s' % e)
                sys.exit(1)
            else:
                format = '%(asctime)s:%(levelname)s:%(name)s:%(pathname)s:%(lineno)d:%(funcName)s %(message)s'
                handler = logging.StreamHandler(stream)
                handler.setLevel(level)
                handler.setFormatter(logging.Formatter(format))
                logging.root.addHandler(handler)
        else:
            # stdout logger
            format = '%(asctime)s:%(levelname)s:%(name)s:%(filename)s:%(lineno)d:%(funcName)s %(message)s'
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(createColoredFormatter(sys.stdout, format))
            handler.setLevel(level)
            logging.root.addHandler(handler)

        #log_format = '%(asctime)s:%(levelname)s:%(name)s:%(filename)s:%(lineno)d:%(funcName)s %(message)s'
        #if self.options.logging_file:
        #    print self.options.logging_file
        #    logging.basicConfig(filename=self.options.logging_file, level=level, format=log_format)
        #else:
        #    logging.basicConfig(stream=sys.stdout, level=level, format=log_format)

        self._handle_options()
        self.handle_application_options()

        return args

    @classmethod
    def run(klass, args=None):
        """
        This static method can be called to run the application.

        It creates the application object, handles options, setups logging, calls
        the main() method, and catches common exceptions.

        You can't do anything after this call, as it *always* finishes with
        a call to sys.exit().

        For example:
        >>> from weboob.application.myapplication import MyApplication
        >>> MyApplication.run()
        """

        if args is None:
            args = [(sys.stdin.encoding and arg.decode(sys.stdin.encoding) or arg) for arg in sys.argv]
        app = klass()

        try:
            try:
                args = app.parse_args(args)
                sys.exit(app.main(args))
            except KeyboardInterrupt:
                print 'Program killed by SIGINT'
                sys.exit(0)
            except EOFError:
                sys.exit(0)
            except ConfigError, e:
                print 'Configuration error: %s' % e
                sys.exit(1)
            except CallErrors, e:
                app.bcall_errors_handler(e)
                sys.exit(1)
        finally:
            app.deinit()

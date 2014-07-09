# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Christophe Benz
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


from __future__ import print_function

import logging
import optparse
from optparse import OptionGroup, OptionParser
import os
import sys
import warnings

from weboob.capabilities.base import ConversionWarning, BaseObject
from weboob.core import Weboob, CallErrors
from weboob.core.backendscfg import BackendsConfig
from weboob.tools.config.iconfig import ConfigError
from weboob.tools.exceptions import FormFieldConversionWarning
from weboob.tools.log import createColoredFormatter, getLogger, settings as log_settings
from weboob.tools.misc import to_unicode
from .results import ResultsConditionError

__all__ = ['BaseApplication']


class MoreResultsAvailable(Exception):
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
    # Configuration and work directory (if None, use the Weboob instance one)
    CONFDIR = None
    # Default configuration dict (can only contain key/values)
    CONFIG = {}
    # Default storage tree
    STORAGE = {}
    # Synopsis
    SYNOPSIS = 'Usage: %prog [-h] [-dqv] [-b backends] ...\n'
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
        if self.CONFDIR is None:
            self.CONFDIR = self.weboob.workdir
        self.config = None
        self.options = None
        self.condition = None
        self.storage = None
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
        self._parser.add_option('-e', '--exclude-backends', help='what backend(s) to exclude (comma separated)')
        self._parser.add_option('-I', '--insecure', action='store_true', help='do not validate SSL')
        logging_options = OptionGroup(self._parser, 'Logging Options')
        logging_options.add_option('-d', '--debug', action='store_true', help='display debug messages')
        logging_options.add_option('-q', '--quiet', action='store_true', help='display only error messages')
        logging_options.add_option('-v', '--verbose', action='store_true', help='display info messages')
        logging_options.add_option('--logging-file', action='store', type='string', dest='logging_file', help='file to save logs')
        logging_options.add_option('-a', '--save-responses', action='store_true', help='save every response')
        self._parser.add_option_group(logging_options)
        self._parser.add_option('--shell-completion', action='store_true', help=optparse.SUPPRESS_HELP)
        self._is_default_count = True

    def deinit(self):
        self.weboob.want_stop()
        self.weboob.deinit()

    def create_storage(self, path=None, klass=None, localonly=False):
        """
        Create a storage object.

        :param path: An optional specific path
        :type path: :class:`str`
        :param klass: What class to instance
        :type klass: :class:`weboob.tools.storage.IStorage`
        :param localonly: If True, do not set it on the :class:`Weboob` object.
        :type localonly: :class:`bool`
        :rtype: :class:`weboob.tools.storage.IStorage`
        """
        if klass is None:
            from weboob.tools.storage import StandardStorage
            klass = StandardStorage

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME + '.storage')
        elif not os.path.sep in path:
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

        :param path: An optional specific path
        :type path: :class:`str`
        :param klass: What class to instance
        :type klass: :class:`weboob.tools.config.iconfig.IConfig`
        :rtype: :class:`weboob.tools.config.iconfig.IConfig`
        """
        if klass is None:
            from weboob.tools.config.iniconfig import INIConfig
            klass = INIConfig

        if path is None:
            path = os.path.join(self.CONFDIR, self.APPNAME)
        elif not os.path.sep in path:
            path = os.path.join(self.CONFDIR, path)

        self.config = klass(path)
        self.config.load(self.CONFIG)

    def main(self, argv):
        """
        Main method

        Called by run
        """
        raise NotImplementedError()

    def load_backends(self, caps=None, names=None, exclude=None, *args, **kwargs):
        if names is None and self.options.backends:
            names = self.options.backends.split(',')
        if exclude is None and self.options.exclude_backends:
            exclude = self.options.exclude_backends.split(',')
        loaded = self.weboob.load_backends(caps, names, exclude=exclude, *args, **kwargs)
        if not loaded:
            logging.info(u'No backend loaded')
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
        if not obj:
            return obj
        if not isinstance(obj, BaseObject):
            return obj

        obj.backend = backend.name
        if fields is None or len(fields) > 0:
            backend.fillobj(obj, fields)
        return obj

    def _do_complete_iter(self, backend, count, fields, res):
        modif = 0
        for i, sub in enumerate(res):
            sub = self._do_complete_obj(backend, fields, sub)
            if self.condition and not self.condition.is_valid(sub):
                modif += 1
            else:
                if count and i - modif == count:
                    if self._is_default_count:
                        raise MoreResultsAvailable()
                    else:
                        return
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

        # Ignore this error.
        if isinstance(error, MoreResultsAvailable):
            return False

        print(u'Error(%s): %s' % (backend.name, error), file=sys.stderr)
        if logging.root.level == logging.DEBUG:
            print(backtrace, file=sys.stderr)
        else:
            return True

    def bcall_errors_handler(self, errors, debugmsg='Use --debug option to print backtraces', ignore=()):
        """
        Handler for the CallErrors exception.

        It calls `bcall_error_handler` for each error.

        :param errors: Object containing errors from backends
        :type errors: :class:`weboob.core.bcall.CallErrors`
        :param debugmsg: Default message asking to enable the debug mode
        :type debugmsg: :class:`basestring`
        :param ignore: Exceptions to ignore
        :type ignore: tuple[:class:`Exception`]
        """
        ask_debug_mode = False
        for backend, error, backtrace in errors.errors:
            if isinstance(error, ignore):
                continue
            elif self.bcall_error_handler(backend, error, backtrace):
                ask_debug_mode = True

        if ask_debug_mode:
            print(debugmsg, file=sys.stderr)

    def parse_args(self, args):
        self.options, args = self._parser.parse_args(args)

        if self.options.shell_completion:
            items = set()
            for option in self._parser.option_list:
                if not option.help is optparse.SUPPRESS_HELP:
                    items.update(str(option).split('/'))
            items.update(self._get_completions())
            print(' '.join(items))
            sys.exit(0)

        if self.options.debug or self.options.save_responses:
            level = logging.DEBUG
        elif self.options.verbose:
            level = logging.INFO
        elif self.options.quiet:
            level = logging.ERROR
        else:
            level = logging.WARNING
        if self.options.insecure:
            log_settings['ssl_insecure'] = True

        # this only matters to developers
        if not self.options.debug and not self.options.save_responses:
            warnings.simplefilter('ignore', category=ConversionWarning)
            warnings.simplefilter('ignore', category=FormFieldConversionWarning)

        handlers = []

        if self.options.save_responses:
            import tempfile
            responses_dirname = tempfile.mkdtemp(prefix='weboob_session_')
            print('Debug data will be saved in this directory: %s' % responses_dirname, file=sys.stderr)
            log_settings['save_responses'] = True
            log_settings['responses_dirname'] = responses_dirname
            handlers.append(self.create_logging_file_handler(os.path.join(responses_dirname, 'debug.log')))

        # file logger
        if self.options.logging_file:
            handlers.append(self.create_logging_file_handler(self.options.logging_file))
        else:
            handlers.append(self.create_default_logger())

        self.setup_logging(level, handlers)

        self._handle_options()
        self.handle_application_options()

        return args

    @classmethod
    def create_default_logger(cls):
        # stdout logger
        format = '%(asctime)s:%(levelname)s:%(name)s:' + cls.VERSION +\
                 ':%(filename)s:%(lineno)d:%(funcName)s %(message)s'
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(createColoredFormatter(sys.stdout, format))
        return handler

    @classmethod
    def setup_logging(cls, level, handlers):
        logging.root.handlers = []

        logging.root.setLevel(level)
        for handler in handlers:
            logging.root.addHandler(handler)

    def create_logging_file_handler(self, filename):
        try:
            stream = open(filename, 'w')
        except IOError as e:
            self.logger.error('Unable to create the logging file: %s' % e)
            sys.exit(1)
        else:
            format = '%(asctime)s:%(levelname)s:%(name)s:' + self.VERSION +\
                     ':%(filename)s:%(lineno)d:%(funcName)s %(message)s'
            handler = logging.StreamHandler(stream)
            handler.setFormatter(logging.Formatter(format))
            return handler

    @classmethod
    def run(cls, args=None):
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

        cls.setup_logging(logging.INFO, [cls.create_default_logger()])

        if args is None:
            args = [(sys.stdin.encoding and isinstance(arg, bytes) and arg.decode(sys.stdin.encoding) or to_unicode(arg)) for arg in sys.argv]

        try:
            app = cls()
        except BackendsConfig.WrongPermissions as e:
            print(e, file=sys.stderr)
            sys.exit(1)

        try:
            try:
                args = app.parse_args(args)
                sys.exit(app.main(args))
            except KeyboardInterrupt:
                print('Program killed by SIGINT', file=sys.stderr)
                sys.exit(0)
            except EOFError:
                sys.exit(0)
            except ConfigError as e:
                print('Configuration error: %s' % e, file=sys.stderr)
                sys.exit(1)
            except CallErrors as e:
                try:
                    app.bcall_errors_handler(e)
                except KeyboardInterrupt:
                    pass
                sys.exit(1)
            except ResultsConditionError as e:
                print('%s' % e, file=sys.stderr)
                sys.exit(1)
        finally:
            app.deinit()

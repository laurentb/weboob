# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon
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


import atexit
from cmd import Cmd
import getpass
import logging
from optparse import OptionGroup
import os
import sys
from copy import deepcopy

from weboob.capabilities.account import ICapAccount, Account, AccountRegisterError
from weboob.capabilities.base import FieldNotFound
from weboob.core import CallErrors
from weboob.core.backendscfg import BackendsConfig, BackendAlreadyExists
from weboob.tools.browser import BrowserUnavailable, BrowserIncorrectPassword
from weboob.tools.value import Value, ValueBool, ValueFloat, ValueInt

from .base import BackendNotFound, BaseApplication
from .formatters.load import FormattersLoader, FormatterLoadError
from .results import ResultsCondition, ResultsConditionException


__all__ = ['ReplApplication', 'NotEnoughArguments']


class NotEnoughArguments(Exception):
    pass

class ReplApplication(Cmd, BaseApplication):
    """
    Base application class for CLI applications.
    """

    SYNOPSIS =  'Usage: %prog [-dqv] [-b backends] [-cnfs] [command [arguments..]]\n'
    SYNOPSIS += '       %prog [--help] [--version]'
    CAPS = None
    DISABLE_REPL = False

    # shell escape strings
    BOLD   = '[37;1m'
    NC     = '[37;0m'    # no color

    EXTRA_FORMATTERS = {}
    DEFAULT_FORMATTER = 'multiline'
    COMMANDS_FORMATTERS = {}

    def __init__(self):
        Cmd.__init__(self)
        # XXX can't use bold prompt because:
        # 1. it causes problems when trying to get history (lines don't start
        #    at the right place).
        # 2. when typing a line longer than term width, cursor goes at start
        #    of the same line instead of new line.
        #self.prompt = self.BOLD + '%s> ' % self.APPNAME + self.NC
        self.prompt = '%s> ' % self.APPNAME
        self.intro = '\n'.join(('Welcome to %s%s%s v%s' % (self.BOLD, self.APPNAME, self.NC, self.VERSION),
                                '',
                                '%s' % self.COPYRIGHT,
                                'This program is free software; you can redistribute it and/or modify',
                                'it under the terms of the GNU General Public License as published by',
                                'the Free Software Foundation, version 3 of the License.',
                                '',
                                'Type "help" to display available commands.',
                                '',
                               ))
        self.weboob_commands = ['backends', 'condition', 'count', 'formatter', 'logging', 'select', 'quit']
        self.hidden_commands = set(['EOF'])

        self.formatters_loader = FormattersLoader()
        for key, klass in self.EXTRA_FORMATTERS.iteritems():
            self.formatters_loader.register_formatter(key, klass)
        self.formatter = None
        self.commands_formatters = self.COMMANDS_FORMATTERS.copy()

        try:
            BaseApplication.__init__(self)
        except BackendsConfig.WrongPermissions, e:
            print e
            sys.exit(1)

        self._parser.format_description = lambda x: self._parser.description

        if self._parser.description is None:
            self._parser.description = ''

        help_str = u''

        app_cmds, weboob_cmds, undoc_cmds = self.get_commands_doc()
        if len(app_cmds) > 0 or len(undoc_cmds) > 0:
            help_str += '%s Commands:\n%s\n\n' % (self.APPNAME.capitalize(), '\n'.join(' %s' % cmd for cmd in sorted(app_cmds + undoc_cmds)))
        if not self.DISABLE_REPL:
            help_str +='Weboob Commands:\n%s\n' % '\n'.join(' %s' % cmd for cmd in weboob_cmds)
        self._parser.description += help_str

        results_options = OptionGroup(self._parser, 'Results Options')
        results_options.add_option('-c', '--condition', help='filter result items to display given a boolean expression')
        results_options.add_option('-n', '--count', default='10', type='int',
                                   help='get a maximum number of results (all backends merged)')
        results_options.add_option('-s', '--select', help='select result item keys to display (comma separated)')
        self._parser.add_option_group(results_options)

        formatting_options = OptionGroup(self._parser, 'Formatting Options')
        available_formatters = self.formatters_loader.get_available_formatters()
        formatting_options.add_option('-f', '--formatter', choices=available_formatters,
                                      help='select output formatter (%s)' % u', '.join(available_formatters))
        formatting_options.add_option('--no-header', dest='no_header', action='store_true', help='do not display header')
        formatting_options.add_option('--no-keys', dest='no_keys', action='store_true', help='do not display item keys')
        self._parser.add_option_group(formatting_options)

        try:
            import readline
        except ImportError:
            pass
        else:
            history_filepath = os.path.join(self.weboob.WORKDIR, '%s_history' % self.APPNAME)
            try:
                readline.read_history_file(history_filepath)
            except IOError:
                pass
            def savehist():
                readline.write_history_file(history_filepath)
            atexit.register(savehist)

        self._interactive = False
        self.enabled_backends = set()

    @property
    def interactive(self):
        return self._interactive

    def caps_included(self, modcaps, caps):
        modcaps = [x.__name__ for x in modcaps]
        if not isinstance(caps, (list,set,tuple)):
            caps = (caps,)
        for cap in caps:
            if not cap in modcaps:
                return False
        return True

    def register_backend(self, name, ask_add=True):
        backend = self.weboob.modules_loader.get_or_load_module(name)
        if not backend:
            print 'Backend "%s" does not exist.' % name
            return None

        if not backend.has_caps(ICapAccount):
            print 'You can\'t register a new account with %s' % name
            return None

        account = Account()
        account.properties = {}
        if backend.website:
            website = 'on website %s' % backend.website
        else:
            website = 'with backend %s' % backend.name
        while 1:
            asked_config = False
            for key, prop in backend.klass.ACCOUNT_REGISTER_PROPERTIES.iteritems():
                if not asked_config:
                    asked_config = True
                    print 'Configuration of new account %s' % website
                    print '-----------------------------%s' % ('-' * len(website))
                p = deepcopy(prop)
                p.set_value(self.ask(prop, default=account.properties[key].value if (key in account.properties) else prop.default))
                account.properties[key] = p
            if asked_config:
                print '-----------------------------%s' % ('-' * len(website))
            try:
                backend.klass.register_account(account)
            except AccountRegisterError, e:
                print u'%s' % e
                if self.ask('Do you want to try again?', default=True):
                    continue
                else:
                    return None
            else:
                break
        backend_config = {}
        for key, value in account.properties.iteritems():
            if key in backend.config:
                backend_config[key] = value.value

        if ask_add and self.ask('Do you want to add the new register account?', default=True):
            return self.add_backend(name, backend_config, ask_register=False)

        return backend_config

    def edit_backend(self, name, params=None):
        return self.add_backend(name, params, True)

    def add_backend(self, name, params=None, edit=False, ask_register=True):
        if params is None:
            params = {}

        if not edit:
            backend = self.weboob.modules_loader.get_or_load_module(name)
        else:
            bname, items = self.weboob.backends_config.get_backend(name)
            backend = self.weboob.modules_loader.get_or_load_module(bname)
            items.update(params)
            params = items
        if not backend:
            print 'Backend "%s" does not exist.' % name
            return None

        # ask for params non-specified on command-line arguments
        asked_config = False
        for key, value in backend.config.iteritems():
            if not asked_config:
                asked_config = True
                print 'Configuration of backend'
                print '------------------------'
            if key not in params or edit:
                params[key] = self.ask(value, default=params[key] if (key in params) else value.default)
            else:
                print u' [%s] %s: %s' % (key, value.description, '(masked)' if value.masked else params[key])
        if asked_config:
            print '------------------------'

        try:
            self.weboob.backends_config.add_backend(name, name, params, edit=edit)
            print 'Backend "%s" successfully %s.' % (name, 'updated' if edit else 'added')
            return name
        except BackendAlreadyExists:
            print 'Backend "%s" is already configured in file "%s"' % (name, self.weboob.backends_config.confpath)
            while self.ask('Add new instance of "%s" backend?' % name, default=False):
                new_name = self.ask('Please give new instance name (could be "%s_1")' % name, regexp=u'^[\d\w_-]+$')
                try:
                    self.weboob.backends_config.add_backend(new_name, name, params)
                    print 'Backend "%s" successfully added.' % new_name
                    return new_name
                except BackendAlreadyExists:
                    print 'Instance "%s" already exists for backend "%s".' % (new_name, name)

    def unload_backends(self, *args, **kwargs):
        unloaded = self.weboob.unload_backends(*args, **kwargs)
        for backend in unloaded.itervalues():
            try:
                self.enabled_backends.remove(backend)
            except KeyError:
                pass
        return unloaded

    def load_backends(self, *args, **kwargs):
        if 'errors' in kwargs:
            errors = kwargs['errors']
        else:
            kwargs['errors'] = errors = []
        ret = super(ReplApplication, self).load_backends(*args, **kwargs)

        for err in errors:
            print >>sys.stderr, 'Error(%s): %s' % (err.backend_name, err)
            if self.ask('Do you want to reconfigure this backend?', default=True):
                self.edit_backend(err.backend_name)
                self.load_backends(names=[err.backend_name])

        for name, backend in ret.iteritems():
            self.enabled_backends.add(backend)
        while len(self.enabled_backends) == 0:
            print 'Warning: there is currently no configured backend for %s' % self.APPNAME
            if not self.ask('Do you want to configure backends?', default=True):
                break

            self.weboob.modules_loader.load_all()
            r = ''
            while r != 'q':
                backends = []
                print '\nAvailable backends:'
                for name, backend in sorted(self.weboob.modules_loader.loaded.iteritems()):
                    if self.CAPS and not self.caps_included(backend.iter_caps(), self.CAPS.__name__):
                        continue
                    backends.append(name)
                    loaded = ' '
                    for bi in self.weboob.iter_backends():
                        if bi.NAME == name:
                            if loaded == ' ':
                                loaded = 'X'
                            elif loaded == 'X':
                                loaded = 2
                            else:
                                loaded += 1
                    print '%s%d)%s [%s] %s%-15s%s (%s)' % (self.BOLD, len(backends), self.NC, loaded,
                                                           self.BOLD, name, self.NC, backend.description)
                print '%sq)%s --stop--\n' % (self.BOLD, self.NC)
                r = self.ask('Select a backend to add (q to stop)', regexp='^(\d+|q)$')

                if r.isdigit():
                    i = int(r) - 1
                    if i < 0 or i >= len(backends):
                        print 'Error: %s is not a valid choice' % r
                        continue
                    name = backends[i]
                    try:
                        inst = self.add_backend(name)
                        if inst:
                            self.load_backends(names=[inst])
                    except (KeyboardInterrupt,EOFError):
                        print '\nAborted.'

            print 'Right right!'

        return ret

    def load_default_backends(self):
        """
        By default loads all backends.

        Applications can overload this method to restrict backends loaded.
        """
        self.load_backends(self.CAPS)

    @classmethod
    def run(klass, args=None):
        try:
            super(ReplApplication, klass).run(args)
        except BackendNotFound, e:
            logging.error(e)

    def parseargs(self, line, nb, req_n=None):
        args = line.strip().split(' ', nb - 1)
        if req_n is not None and (len(args) < req_n or req_n < 2 and line == ''):
            raise NotEnoughArguments('Command needs %d arguments' % req_n)

        if len(args) < nb:
            args += tuple([None for i in xrange(nb - len(args))])
        return args

    def postcmd(self, stop, line):
        """
        This REPL method is overrided to return None instead of integers
        to prevent stopping cmdloop().
        """
        if not isinstance(stop, bool):
            stop = None
        return stop

    def bcall_error_handler(self, backend, error, backtrace):
        """
        Handler for an exception inside the CallErrors exception.

        This method can be overrided to support more exceptions types.
        """
        if isinstance(error, BrowserIncorrectPassword):
            msg = unicode(error)
            if not msg:
                msg = 'invalid login/password.'
            print >>sys.stderr, 'Error(%s): %s' % (backend.name, msg)
            if self.ask('Do you want to reconfigure this backend?', default=True):
                self.unload_backends(names=[backend.name])
                self.edit_backend(backend.name)
                self.load_backends(names=[backend.name])
        elif isinstance(error, BrowserUnavailable):
            msg = unicode(error)
            if not msg:
                msg = 'website is unavailable.'
            print >>sys.stderr, u'Error(%s): %s' % (backend.name, msg)
        elif isinstance(error, NotImplementedError):
            print >>sys.stderr, u'Error(%s): this feature is not supported yet by this backend.' % backend.name
            print >>sys.stderr, u'      %s   To help the maintainer of this backend implement this feature,' % (' ' * len(backend.name))
            print >>sys.stderr, u'      %s   please contact: %s <%s>' % (' ' * len(backend.name), backend.MAINTAINER, backend.EMAIL)
        else:
            print >>sys.stderr, u'Error(%s): %s' % (backend.name, error)
            if logging.root.level == logging.DEBUG:
                print >>sys.stderr, backtrace
            else:
                return True

    def bcall_errors_handler(self, errors):
        """
        Handler for the CallErrors exception.
        """
        ask_debug_mode = False
        for backend, error, backtrace in errors.errors:
            if self.bcall_error_handler(backend, error, backtrace):
                ask_debug_mode = True

        if ask_debug_mode:
            if self.interactive:
                print >>sys.stderr, 'Use "logging debug" option to print backtraces.'
            else:
                print >>sys.stderr, 'Use --debug option to print backtraces.'

    def onecmd(self, line):
        """
        This REPL method is overrided to catch some particular exceptions.
        """
        cmd, arg, ignored = self.parseline(line)

        # Set the right formatter for the command.
        try:
            formatter_name = self.commands_formatters[cmd]
        except KeyError:
            formatter_name = self.DEFAULT_FORMATTER
        self.set_formatter(formatter_name)

        try:
            return super(ReplApplication, self).onecmd(line)
        except CallErrors, e:
            self.bcall_error_handler(e)
        except NotEnoughArguments, e:
            print >>sys.stderr, 'Error: no enough arguments.'
        except (KeyboardInterrupt,EOFError):
            # ^C during a command process doesn't exit application.
            print '\nAborted.'

    def main(self, argv):
        cmd_args = argv[1:]
        if cmd_args:
            if cmd_args[0] == 'help':
                self._parser.print_help()
                self._parser.exit()
            cmd_line = ' '.join(cmd_args)
            cmds = cmd_line.split(';')
            for cmd in cmds:
                ret = self.onecmd(cmd)
                if ret:
                    return ret
        elif self.DISABLE_REPL:
            self._parser.print_help()
            self._parser.exit()
        else:
            self.intro += '\nLoaded backends: %s\n' % ', '.join(sorted(backend.name for backend in self.weboob.iter_backends()))
            self._interactive = True
            self.cmdloop()

    def do(self, function, *args, **kwargs):
        """
        Call Weboob.do(), passing count and selected fields given by user.
        """
        backends = kwargs.pop('backends', None)
        kwargs['backends'] = self.enabled_backends if backends is None else backends
        fields = self.selected_fields
        if fields == '$direct':
            fields = []
        elif fields == '$full':
            fields = None
        return self.weboob.do(self._do_complete, self.options.count, fields, function, *args, **kwargs)

    # options related methods

    def _handle_options(self):
        if self.options.formatter:
            self.commands_formatters = {}
            self.DEFAULT_FORMATTER = self.options.formatter
        self.set_formatter(self.DEFAULT_FORMATTER)

        if self.options.select:
            self.selected_fields = self.options.select.split(',')
        else:
            self.selected_fields = '$direct'

        if self.options.condition:
            self.condition = ResultsCondition(self.options.condition)
        else:
            self.condition = None

        if self.options.count == 0:
            self._parser.error('Count must be at least 1, or negative for infinite')
        elif self.options.count < 0:
            # infinite search
            self.options.count = None

        self.load_default_backends()

    # default REPL commands

    def do_quit(self, arg):
        """
        Quit the application.
        """
        return True

    def do_EOF(self, arg):
        """
        Quit the command line interpreter when ^D is pressed.
        """
        # print empty line for the next shell prompt to appear on the first column of the terminal
        print
        return self.do_quit(arg)

    def get_command_help(self, command, short=False):
        try:
            doc = getattr(self, 'do_' + command).__doc__
        except AttributeError:
            return None
        if doc:
            doc = '\n'.join(line.strip() for line in doc.strip().split('\n'))
            if short:
                doc = doc.split('\n')[0]
                if not doc.startswith(command):
                    doc = command
            return doc

    def get_commands_doc(self):
        names = set(name for name in self.get_names() if name.startswith('do_'))
        application_cmds_doc = []
        weboob_cmds_doc = []
        cmds_undoc = []
        for name in sorted(names):
            cmd = name[3:]
            if cmd in self.hidden_commands.union(self.weboob_commands).union(['help']):
                continue
            elif getattr(self, name).__doc__:
                short_help = '    %s' % self.get_command_help(cmd, short=True)
                application_cmds_doc.append(short_help)
            else:
                cmds_undoc.append(cmd)
        for cmd in self.weboob_commands:
            short_help = '    %s' % self.get_command_help(cmd, short=True)
            weboob_cmds_doc.append(short_help)
        return application_cmds_doc, weboob_cmds_doc, cmds_undoc

    def do_help(self, arg=None):
        if arg:
            cmd_names = set(name[3:] for name in self.get_names() if name.startswith('do_'))
            if arg in cmd_names:
                command_help = self.get_command_help(arg)
                if command_help is None:
                    logging.warning(u'Command "%s" is undocumented' % arg)
                else:
                    self.stdout.write('%s\n' % command_help)
            else:
                print 'Unknown command: "%s"' % arg
        else:
            application_cmds_doc, weboob_cmds_doc, undoc_cmds_doc = self.get_commands_doc()

            application_cmds_header = '%s commands' % self.APPNAME.capitalize()
            self.stdout.write('%s\n%s\n' % (application_cmds_header, '-' * len(application_cmds_header)))
            self.stdout.write('\n'.join(application_cmds_doc) + '\n\n')
            weboob_cmds_header = 'Generic Weboob commands'
            self.stdout.write('%s\n%s\n' % (weboob_cmds_header, '-' * len(weboob_cmds_header)))
            self.stdout.write('\n'.join(weboob_cmds_doc) + '\n\n')
            self.print_topics(self.undoc_header, undoc_cmds_doc, 15,80)
            self.stdout.write('Type "help <command>" for more info about a command.\n')

    def emptyline(self):
        """
        By default, an emptyline repeats the previous command.
        Overriding this function disables this behaviour.
        """
        pass

    def default(self, line):
        print 'Unknown command: "%s"' % line

    def completenames(self, text, *ignored):
        return [name for name in Cmd.completenames(self, text, *ignored) if name not in self.hidden_commands]

    def complete(self, text, state):
        """
        Override of the Cmd.complete() method to:
        - add a space at end of proposals
        - display only proposals for words which match the
          text already written by user.
        """
        super(ReplApplication, self).complete(text, state)

        # When state = 0, Cmd.complete() set the 'completion_matches' attribute by
        # calling the completion function. Then, for other states, it only try to
        # get the right item in list.
        # So that's the good place to rework the choices.
        if state == 0:
            self.completion_matches = [choice for choice in self.completion_matches if choice.startswith(text)]

        try:
            return '%s ' % self.completion_matches[state]
        except IndexError:
            return None

    def do_backends(self, line):
        """
        backends [ACTION] [BACKEND_NAME]...

        Select used backends.

        ACTION is one of the following (default: list):
            * enable    enable given backends
            * disable   disable given backends
            * only      enable given backends and disable the others
            * list      display enabled and available backends
            * add       add a backend
            * register  register a new account on a website
            * edit      edit a backend
            * remove    remove a backend
        """
        line = line.strip()
        if line:
            args = line.split()
        else:
            args = ['list']

        action = args[0]
        given_backend_names = args[1:]

        if action not in ('add', 'register'):
            skipped_backend_names = []
            for backend_name in given_backend_names:
                if backend_name not in [backend.name for backend in self.weboob.iter_backends()]:
                    print 'Backend "%s" does not exist => skipping.' % backend_name
                    skipped_backend_names.append(backend_name)
            for skipped_backend_name in skipped_backend_names:
                given_backend_names.remove(skipped_backend_name)

        if action in ('enable', 'disable', 'only', 'add', 'register', 'remove'):
            if not given_backend_names:
                print 'Please give at least a backend name.'
                return

        given_backends = set(backend for backend in self.weboob.iter_backends() if backend.name in given_backend_names)

        if action == 'enable':
            for backend in given_backends:
                self.enabled_backends.add(backend)
        elif action == 'disable':
            for backend in given_backends:
                try:
                    self.enabled_backends.remove(backend)
                except KeyError:
                    print '%s is not enabled' % backend.name
        elif action == 'only':
            self.enabled_backends = set()
            for backend in given_backends:
                self.enabled_backends.add(backend)
        elif action == 'list':
            enabled_backends_names = set(backend.name for backend in self.enabled_backends)
            disabled_backends_names = set(backend.name for backend in self.weboob.iter_backends()) - enabled_backends_names
            print 'Enabled: %s' % ', '.join(enabled_backends_names)
            if len(disabled_backends_names) > 0:
                print 'Disabled: %s' % ', '.join(disabled_backends_names)
        elif action == 'add':
            for name in given_backend_names:
                instname = self.add_backend(name)
                if instname:
                    self.load_backends(names=[instname])
        elif action == 'register':
            for name in given_backend_names:
                instname = self.register_backend(name)
                if isinstance(instname, basestring):
                    self.load_backends(names=[instname])
        elif action == 'edit':
            for backend in given_backends:
                enabled = backend in self.enabled_backends
                self.unload_backends(names=[backend.name])
                self.edit_backend(backend.name)
                for newb in self.load_backends(names=[backend.name]).itervalues():
                    if not enabled:
                        self.enabled_backends.remove(newb)
        elif action == 'remove':
            for backend in given_backends:
                self.weboob.backends_config.remove_backend(backend.name)
                self.unload_backends(backend.name)
        else:
            print 'Unknown action: "%s"' % action
            return 1

        if len(self.enabled_backends) == 0:
            print 'Warning: no more backends are loaded. %s is probably unusable.' % self.APPNAME.capitalize()

    def complete_backends(self, text, line, begidx, endidx):
        choices = []
        commands = ['enable', 'disable', 'only', 'list', 'add', 'register', 'edit', 'remove']
        available_backends_names = set(backend.name for backend in self.weboob.iter_backends())
        enabled_backends_names = set(backend.name for backend in self.enabled_backends)

        args = line.split(' ')
        if len(args) == 2:
            choices = commands
        elif len(args) >= 3:
            if args[1] == 'enable':
                choices = sorted(available_backends_names - enabled_backends_names)
            elif args[1] == 'only':
                choices = sorted(available_backends_names)
            elif args[1] == 'disable':
                choices = sorted(enabled_backends_names)
            elif args[1] in ('add', 'register') and len(args) == 3:
                self.weboob.modules_loader.load_all()
                for name, module in sorted(self.weboob.modules_loader.loaded.iteritems()):
                    if not self.CAPS or self.caps_included(module.iter_caps(), self.CAPS.__name__):
                        choices.append(name)
            elif args[1] == 'edit':
                choices = sorted(available_backends_names)
            elif args[1] == 'remove':
                choices = sorted(available_backends_names)

        return choices

    def do_logging(self, line):
        """
        logging [LEVEL]

        Set logging level.

        Availables: debug, info, warning, error.
        * quiet is an alias for error
        * default is an alias for warning
        """
        args = self.parseargs(line, 1, 0)
        levels = (('debug',   logging.DEBUG),
                  ('info',    logging.INFO),
                  ('warning', logging.WARNING),
                  ('error',   logging.ERROR),
                  ('quiet',   logging.ERROR),
                  ('default', logging.WARNING)
                 )

        if not args[0]:
            current = None
            for label, level in levels:
                if logging.root.level == level:
                    current = label
                    break
            print 'Current level: %s' % current
            return

        levels = dict(levels)
        try:
            level = levels[args[0]]
        except KeyError:
            print >>sys.stderr, 'Level "%s" does not exist.' % args[0]
            print >>sys.stderr, 'Availables: %s' % ' '.join(levels.iterkeys())
        else:
            logging.root.setLevel(level)
            for handler in logging.root.handlers:
                handler.setLevel(level)

    def complete_logging(self, text, line, begidx, endidx):
        levels = ('debug', 'info', 'warning', 'error', 'quiet', 'default')
        args = line.split(' ')
        if len(args) == 2:
            return levels
        return ()

    def do_condition(self, line):
        """
        condition [EXPRESSION | off]

        If an argument is given, set the condition expression used to filter the results.
        If the "off" value is given, conditional filtering is disabled.

        If no argument is given, print the current condition expression.
        """
        line = line.strip()
        if line:
            if line == 'off':
                self.condition = None
            else:
                try:
                    self.condition = ResultsCondition(line)
                except ResultsConditionException, e:
                    print e
        else:
            if self.condition is None:
                print 'No condition is set.'
            else:
                print str(self.condition)

    def do_count(self, line):
        """
        count [NUMBER | off]

        If an argument is given, set the maximum number of results fetched.
        NUMBER must be at least 1.
        "off" value disables counting, and allows infinite searches.

        If no argument is given, print the current count value.
        """
        line = line.strip()
        if line:
            if line == 'off':
                self.options.count = None
            else:
                try:
                    count = int(line)
                except ValueError:
                    print 'Could not interpret "%s" as a number.' % line
                else:
                    if count > 0:
                        self.options.count = count
                    else:
                        print 'Number must be at least 1.'
        else:
            if self.options.count is None:
                print 'Counting disabled.'
            else:
                print self.options.count

    def complete_formatter(self, text, line, *ignored):
        formatters = self.formatters_loader.get_available_formatters()
        commands = ['list', 'option'] + formatters
        options = ['header', 'keys']
        option_values = ['on', 'off']

        args = line.split(' ')
        if len(args) == 2:
            return commands
        if args[1] == 'option':
            if len(args) == 3:
                return options
            if len(args) == 4:
                return option_values
        elif args[1] in formatters:
            return list(set(name[3:] for name in self.get_names() if name.startswith('do_')))

    def do_formatter(self, line):
        """
        formatter [list | FORMATTER [COMMAND] | option OPTION_NAME [on | off]]

        If a FORMATTER is given, set the formatter to use.
        You can add a COMMAND to apply the formatter change only to
        a given command.

        If the argument is "list", print the available formatters.

        If the argument is "option", set the formatter options.
        Valid options are: header, keys.
        If on/off value is given, set the value of the option.
        If not, print the current value for the option.

        If no argument is given, print the current formatter.
        """
        args = line.strip().split()
        if args:
            if args[0] == 'list':
                print ', '.join(self.formatters_loader.get_available_formatters())
            elif args[0] == 'option':
                if len(args) > 1:
                    if len(args) == 2:
                        if args[1] == 'header':
                            print 'off' if self.options.no_header else 'on'
                        elif args[1] == 'keys':
                            print 'off' if self.options.no_keys else 'on'
                    else:
                        if args[2] not in ('on', 'off'):
                            print 'Invalid value "%s". Please use "on" or "off" values.' % args[2]
                        else:
                            if args[1] == 'header':
                                self.options.no_header = True if args[2] == 'off' else False
                            elif args[1] == 'keys':
                                self.options.no_keys = True if args[2] == 'off' else False
                else:
                    print 'Don\'t know which option to set. Available options: header, keys.'
            else:
                if args[0] in self.formatters_loader.get_available_formatters():
                    if len(args) > 1:
                        self.commands_formatters[args[1]] = self.set_formatter(args[0])
                    else:
                        self.commands_formatters = {}
                        self.DEFAULT_FORMATTER = self.set_formatter(args[0])
                else:
                    print 'Formatter "%s" is not available.\n' \
                            'Available formatters: %s.' % (args[0], ', '.join(self.formatters_loader.get_available_formatters()))
        else:
            print 'Default formatter: %s' % self.DEFAULT_FORMATTER
            for key, klass in self.commands_formatters.iteritems():
                print 'Command "%s": %s' % (key, klass)

    def do_select(self, line):
        """
        select [FIELD_NAME]... | "$direct" | "$full"

        If an argument is given, set the selected fields.
        $direct selects all fields loaded in one http request.
        $full selects all fields using as much http requests as necessary.

        If no argument is given, print the currently selected fields.
        """
        line = line.strip()
        if line:
            split = line.split()
            if len(split) == 1 and split[0] in ('$direct', '$full'):
                self.selected_fields = split[0]
            else:
                self.selected_fields = split
        else:
            if isinstance(self.selected_fields, basestring):
                print self.selected_fields
            else:
                print ' '.join(self.selected_fields)


    # user interaction related methods

    def ask(self, question, default=None, masked=False, regexp=None, choices=None):
        """
        Ask a question to user.

        @param question  text displayed (str)
        @param default  optional default value (str)
        @param masked  if True, do not show typed text (bool)
        @param regexp  text must match this regexp (str)
        @param choices  choices to do (list)
        @return  entered text by user (str)
        """

        if isinstance(question, Value):
            v = deepcopy(question)
            if default:
                v.default = default
            if masked:
                v.masked = masked
            if regexp:
                v.regexp = regexp
            if choices:
                v.choices = choices
        else:
            if isinstance(default, bool):
                klass = ValueBool
            elif isinstance(default, float):
                klass = ValueFloat
            elif isinstance(default, (int,long)):
                klass = ValueInt
            else:
                klass = Value

            v = klass(label=question, default=default, masked=masked, regexp=regexp, choices=choices)

        question = v.label
        if v.id:
            question = u'[%s] %s' % (v.id, question)

        if isinstance(v, ValueBool):
            question = u'%s (%s/%s)' % (question, 'Y' if v.default else 'y', 'n' if v.default else 'N')
        elif v.choices:
            question = u'%s (%s)' % (question, '/'.join([(s.upper() if s == v.default else s) for s in (v.choices.iterkeys())]))
        elif default not in (None, '') and not v.masked:
            question = u'%s [%s]' % (question, v.default)

        if v.masked:
            question = u'%s (hidden input)' % question

        question += ': '

        while True:
            line = getpass.getpass(question) if v.masked else raw_input(question)
            if not line and v.default is not None:
                line = v.default
            if isinstance(line, str):
                line = line.decode('utf-8')

            try:
                v.set_value(line)
            except ValueError, e:
                print 'Error: %s' % e
            else:
                break

        return v.value

    # formatting related methods

    def set_formatter(self, name):
        """
        Set the current formatter from name.

        It returns the name of the formatter which has been really set.
        """
        try:
            self.formatter = self.formatters_loader.build_formatter(name)
        except FormatterLoadError, e:
            print '%s' % e
            if self.DEFAULT_FORMATTER == name:
                self.DEFAULT_FORMATTER = ReplApplication.DEFAULT_FORMATTER
            print 'Falling back to "%s".' % (self.DEFAULT_FORMATTER)
            self.formatter = self.formatters_loader.build_formatter(self.DEFAULT_FORMATTER)
            name = self.DEFAULT_FORMATTER
        if self.options.no_header:
            self.formatter.display_header = False
        if self.options.no_keys:
            self.formatter.display_keys = False
        if self.interactive:
            self.formatter.interactive = True
        return name

    def set_formatter_header(self, string):
        self.formatter.set_header(string)

    def format(self, result):
        fields = self.selected_fields
        if fields in ('$direct', '$full'):
            fields = None
        try:
            self.formatter.format(obj=result, selected_fields=fields, condition=self.condition)
        except FieldNotFound, e:
            print e
        except ResultsConditionException, e:
            print e

    def flush(self):
        self.formatter.flush()

    def parse_id(self, _id):
        try:
            _id, backend_name = _id.rsplit('@', 1)
        except ValueError:
            backend_name = None
        return _id, backend_name

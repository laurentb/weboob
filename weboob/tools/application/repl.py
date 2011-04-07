# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Christophe Benz, Romain Bignon
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


import atexit
from cmd import Cmd
import logging
from optparse import OptionGroup, OptionParser, IndentedHelpFormatter
import os
import sys

from weboob.capabilities.base import FieldNotFound
from weboob.core import CallErrors
from weboob.core.modules import ModuleLoadError
from weboob.tools.application.formatters.iformatter import MandatoryFieldsNotFound
from weboob.tools.misc import to_unicode
from weboob.tools.ordereddict import OrderedDict

from .console import BackendNotGiven, ConsoleApplication
from .formatters.load import FormattersLoader, FormatterLoadError
from .results import ResultsCondition, ResultsConditionError


__all__ = ['ReplApplication', 'NotEnoughArguments']


class NotEnoughArguments(Exception):
    pass

class ReplOptionParser(OptionParser):
    def format_option_help(self, formatter=None):
        if not formatter:
            formatter = self.formatter

        return '%s\n%s' % (formatter.format_commands(self.commands),
                           OptionParser.format_option_help(self, formatter))

class ReplOptionFormatter(IndentedHelpFormatter):
    def format_commands(self, commands):
        s = u''
        for section, cmds in commands.iteritems():
            if len(s) > 0:
                s += '\n'
            s += '%s Commands:\n' % section
            for c in cmds:
                c = c.split('\n')[0]
                s += '    %s\n' % c
        return s

class ReplApplication(Cmd, ConsoleApplication):
    """
    Base application class for Repl applications.
    """

    SYNOPSIS =  'Usage: %prog [-dqv] [-b backends] [-cnfs] [command [arguments..]]\n'
    SYNOPSIS += '       %prog [--help] [--version]'
    DISABLE_REPL = False

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
                                'This program is free software: you can redistribute it and/or modify',
                                'it under the terms of the GNU Affero General Public License as published by',
                                'the Free Software Foundation, either version 3 of the License, or',
                                '(at your option) any later version.',
                                '',
                                'Type "help" to display available commands.',
                                '',
                               ))
        self.weboob_commands = ['backends', 'condition', 'count', 'formatter', 'inspect', 'logging', 'select', 'quit']
        self.hidden_commands = set(['EOF'])

        self.formatters_loader = FormattersLoader()
        for key, klass in self.EXTRA_FORMATTERS.iteritems():
            self.formatters_loader.register_formatter(key, klass)
        self.formatter = None
        self.commands_formatters = self.COMMANDS_FORMATTERS.copy()

        ConsoleApplication.__init__(self, ReplOptionParser(self.SYNOPSIS, version=self._get_optparse_version()))

        commands_help = self.get_commands_doc()
        self._parser.commands = commands_help
        self._parser.formatter = ReplOptionFormatter()

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
        formatting_options.add_option('-O', '--outfile', dest='outfile', help='file to export result')
        self._parser.add_option_group(formatting_options)

        self._interactive = False

    @property
    def interactive(self):
        return self._interactive

    def main(self, argv):
        cmd_args = argv[1:]
        if cmd_args:
            if cmd_args[0] == 'help':
                self._parser.print_help()
                self._parser.exit()
            cmd_line = u' '.join(cmd_args)
            cmds = cmd_line.split(';')
            for cmd in cmds:
                ret = self.onecmd(cmd)
                if ret:
                    return ret
        elif self.DISABLE_REPL:
            self._parser.print_help()
            self._parser.exit()
        else:
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

            self.intro += '\nLoaded backends: %s\n' % ', '.join(sorted(backend.name for backend in self.weboob.iter_backends()))
            self._interactive = True
            self.cmdloop()

    def do(self, function, *args, **kwargs):
        """
        Call Weboob.do(), passing count and selected fields given by user.
        """
        backends = kwargs.pop('backends', None)
        kwargs['backends'] = self.enabled_backends if backends is None else backends
        kwargs['condition'] = self.condition
        fields = self.selected_fields
        if fields == '$direct':
            fields = []
        elif fields == '$full':
            fields = None
        return self.weboob.do(self._do_complete, self.options.count, fields, function, *args, **kwargs)

    # -- command tools ------------
    def parse_command_args(self, line, nb, req_n=None):
        if line.strip() == '':
            # because ''.split() = ['']
            args = []
        else:
            args = line.strip().split(' ', nb - 1)
        if req_n is not None and (len(args) < req_n):
            raise NotEnoughArguments('Command needs %d arguments' % req_n)

        if len(args) < nb:
            args += tuple(None for i in xrange(nb - len(args)))
        return args

    # -- cmd.Cmd methods ---------
    def postcmd(self, stop, line):
        """
        This REPL method is overrided to return None instead of integers
        to prevent stopping cmdloop().
        """
        if not isinstance(stop, bool):
            stop = None
        return stop

    def onecmd(self, line):
        """
        This REPL method is overrided to catch some particular exceptions.
        """
        line = to_unicode(line)
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
            self.bcall_errors_handler(e)
        except BackendNotGiven, e:
            print >>sys.stderr, 'Error: %s' % str(e)
        except NotEnoughArguments, e:
            print >>sys.stderr, 'Error: not enough arguments. %s' % str(e)
        except (KeyboardInterrupt, EOFError):
            # ^C during a command process doesn't exit application.
            print '\nAborted.'

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

    def path_completer(self, arg):
        dirname = os.path.dirname(arg)
        try:
            childs = os.listdir(dirname or '.')
        except OSError:
            return ()
        l = []
        for child in childs:
            path = os.path.join(dirname, child)
            if os.path.isdir(path):
                child += '/'
            l.append(child)
        return l

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
            match = self.completion_matches[state]
        except IndexError:
            return None
        else:
            if match[-1] != '/':
                return '%s ' % match
            return match

    # -- errors management -------------
    def bcall_error_handler(self, backend, error, backtrace):
        """
        Handler for an exception inside the CallErrors exception.

        This method can be overrided to support more exceptions types.
        """
        if isinstance(error, ResultsConditionError):
            print >>sys.stderr, u'Error(%s): condition error: %s' % (backend.name, error)
        else:
            return super(ReplApplication, self).bcall_error_handler(backend, error, backtrace)

    # -- options related methods -------------
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

        return super(ReplApplication, self)._handle_options()

    def get_command_help(self, command, short=False):
        try:
            doc = getattr(self, 'do_' + command).__doc__
        except AttributeError:
            return None
        if doc:
            doc = '\n'.join(line.strip() for line in doc.strip().split('\n'))
            if not doc.startswith(command):
                doc = '%s\n\n%s' % (command, doc)
            if short:
                doc = doc.split('\n')[0]
                if not doc.startswith(command):
                    doc = command

            return doc

    def get_commands_doc(self):
        names = set(name for name in self.get_names() if name.startswith('do_'))
        appname = self.APPNAME.capitalize()
        d = OrderedDict(((appname, []), ('Weboob', [])))

        for name in sorted(names):
            cmd = name[3:]
            if cmd in self.hidden_commands.union(self.weboob_commands).union(['help']):
                continue
            elif getattr(self, name).__doc__:
                d[appname].append(self.get_command_help(cmd))
            else:
                d[appname].append(cmd)
        if not self.DISABLE_REPL:
            for cmd in self.weboob_commands:
                d['Weboob'].append(self.get_command_help(cmd))

        return d

    # -- default REPL commands ---------

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
            cmds = self._parser.formatter.format_commands(self._parser.commands)
            self.stdout.write('%s\n' % cmds)
            self.stdout.write('Type "help <command>" for more info about a command.\n')

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

        for backend_name in given_backend_names:
            if action in ('add', 'register'):
                try:
                    module = self.weboob.modules_loader.get_or_load_module(backend_name)
                except ModuleLoadError:
                    print >>sys.stderr, 'Backend "%s" does not exist.' % backend_name
                    return 1
                else:
                    if self.CAPS and not self.caps_included(module.iter_caps(), self.CAPS.__name__):
                        print >>sys.stderr, 'Backend "%s" is not supported by this application => skipping.' % backend_name
                        return 1
            else:
                if backend_name not in [backend.name for backend in self.weboob.iter_backends()]:
                    print >>sys.stderr, 'Backend "%s" does not exist => skipping.' % backend_name
                    return 1

        if action in ('enable', 'disable', 'only', 'add', 'register', 'edit', 'remove'):
            if not given_backend_names:
                print >>sys.stderr, 'Please give at least a backend name.'
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

    def complete_logging(self, text, line, begidx, endidx):
        levels = ('debug', 'info', 'warning', 'error', 'quiet', 'default')
        args = line.split(' ')
        if len(args) == 2:
            return levels
        return ()

    def do_logging(self, line):
        """
        logging [LEVEL]

        Set logging level.

        Availables: debug, info, warning, error.
        * quiet is an alias for error
        * default is an alias for warning
        """
        args = self.parse_command_args(line, 1, 0)
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
                except ResultsConditionError, e:
                    print >>sys.stderr, '%s' % e
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

    def complete_inspect(self, text, line, begidx, endidx):
        return sorted(set(backend.name for backend in self.enabled_backends))

    def do_inspect(self, line):
        """
        inspect BACKEND_NAME

        Display the HTML string of the current page of the specified backend's browser.

        If webkit_mechanize_browser Python module is installed, HTML is displayed in a WebKit GUI.
        """
        if len(self.enabled_backends) == 1:
            backend = list(self.enabled_backends)[0]
        else:
            backend_name = line.strip()
            if not backend_name:
                print 'Please specify a backend name.'
                return
            backends = set(backend for backend in self.enabled_backends if backend.name == backend_name)
            if not backends:
                print 'No backend found for "%s"' % backend_name
                return
            backend = backends.pop()
        if not hasattr(backend, '_browser'):
            print 'No browser created for backend "%s" yet. Please invoke a command before.' % backend.name
            return
        browser = backend._browser
        data = browser.parser.tostring(browser.page.document)
        try:
            from webkit_mechanize_browser.browser import Browser
            from weboob.tools.inspect import Page
        except ImportError:
            print data
        else:
            page = Page(core=browser, data=data, uri=browser._response.geturl())
            browser = Browser(view=page.view)

    # -- formatting related methods -------------
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
        if self.options.outfile:
            self.formatter.outfile = self.options.outfile
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
            self.formatter.format(obj=result, selected_fields=fields)
        except FieldNotFound, e:
            print e
        except MandatoryFieldsNotFound, e:
            print >> sys.stderr, '%s Hint: select missing fields or use another formatter (ex: multiline).' % e

    def flush(self):
        self.formatter.flush()

# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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

import atexit
import cmd
from cStringIO import StringIO
from functools import partial
import getpass
from inspect import getargspec
import logging
from optparse import OptionGroup, OptionParser
import os
import re
import subprocess
import sys

from weboob.capabilities.base import FieldNotFound
from weboob.core import CallErrors
from weboob.core.backendscfg import BackendsConfig
from weboob.tools.misc import iter_fields

from .base import BackendNotFound, BaseApplication
from .formatters.load import formatters as available_formatters, load_formatter
from .results import ResultsCondition, ResultsConditionException


__all__ = ['ReplApplication']


class ReplApplication(cmd.Cmd, BaseApplication):
    """
    Base application class for CLI applications.
    """

    SYNOPSIS =  'Usage: %prog [-dqv] [-b backends] [-cnfs] [command [arguments..]]\n'
    SYNOPSIS += '       %prog [--help] [--version]'

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt = '%s> ' % self.APPNAME
        self.intro = '\n'.join(('Welcome to %s v%s' % (self.APPNAME, self.VERSION),
                                '',
                                '%s' % self.COPYRIGHT,
                                'This program is free software; you can redistribute it and/or modify',
                                'it under the terms of the GNU General Public License as published by',
                                'the Free Software Foundation, version 3 of the License.',
                                '',
                                'Type "help" to display available commands.',
                                '',
                               ))
        self.weboob_commands = ['backends', 'condition', 'count', 'formatter', 'select', 'quit']
        self.hidden_commands = set(['EOF'])

        option_parser = OptionParser(self.SYNOPSIS, version=self._get_optparse_version())
        app_options = OptionGroup(option_parser, '%s Options' % self.APPNAME.capitalize())
        self.add_application_options(app_options)
        option_parser.add_option_group(app_options)

        try:
            BaseApplication.__init__(self, option_parser=option_parser)
        except BackendsConfig.WrongPermissions, e:
            print e
            sys.exit(1)

        self._parser.format_description = lambda x: self._parser.description

        if self._parser.description is None:
            self._parser.description = ''

        app_cmds, weboob_cmds, undoc_cmds = self.get_commands_doc()
        help_str = '%s Commands:\n%s\n\n' % (self.APPNAME, '\n'.join(' %s' % cmd for cmd in sorted(app_cmds + undoc_cmds)))
        help_str +='Weboob Commands:\n%s\n' % '\n'.join(' %s' % cmd for cmd in weboob_cmds)
        self._parser.description += help_str

        results_options = OptionGroup(self._parser, 'Results Options')
        results_options.add_option('-c', '--condition', help='filter result items to display given a boolean expression')
        results_options.add_option('-n', '--count', default='10', type='int',
                                   help='get a maximum number of results (all backends merged)')
        results_options.add_option('-s', '--select', help='select result item keys to display (comma separated)')
        self._parser.add_option_group(results_options)

        formatting_options = OptionGroup(self._parser, 'Formatting Options')
        formatting_options.add_option('-f', '--formatter', choices=available_formatters,
                                      help='select output formatter (%s)' % u','.join(available_formatters))
        formatting_options.add_option('--no-header', dest='no_header', action='store_true', help='do not display header')
        formatting_options.add_option('--no-keys', dest='no_keys', action='store_true', help='do not display item keys')
        self._parser.add_option_group(formatting_options)

        try:
            import readline
        except ImportError:
            pass
        finally:
            history_filepath = os.path.join(self.weboob.WORKDIR, '%s_history' % self.APPNAME)
            try:
                readline.read_history_file(history_filepath)
            except IOError:
                pass
            def savehist():
                readline.write_history_file(history_filepath)
            atexit.register(savehist)

    def set_requested_backends(self, requested_backends):
        self.load_default_backends()
        if requested_backends:
            self.enabled_backends = set(backend for backend in self.weboob.iter_backends()
                                        if backend.name in requested_backends)
        else:
            self.enabled_backends = list(self.weboob.iter_backends())

    def load_default_backends(self):
        """
        By default loads all backends.

        Applications can overload this method to restrict backends loaded.
        """
        self.load_backends()

    @classmethod
    def run(klass, args=None):
        try:
            super(ReplApplication, klass).run(args)
        except BackendNotFound, e:
            logging.error(e)

    def main(self, argv):
        cmd_args = argv[1:]
        if cmd_args:
            if cmd_args[0] == 'help':
                self._parser.print_help()
                self._parser.exit()
            cmd_line = ' '.join(cmd_args)
            cmds = cmd_line.split(';')
            for cmd in cmds:
                self.onecmd(cmd)
        else:
            self.intro += '\nLoaded backends: %s\n' % ', '.join(sorted(backend.name for backend in self.weboob.iter_backends()))
            self.cmdloop()

    def do(self, function, *args, **kwargs):
        """
        Call Weboob.do(), passing count and selected fields given by user.
        """
        backends = kwargs.pop('backends', None)
        kwargs['backends'] = self.enabled_backends if backends is None else backends
        fields = self.selected_fields
        if fields == '$direct':
            fields = None
        elif fields == '$full':
            fields = [k for k, v in iter_fields(obj)]
        try:
            for values in self.weboob.do(self._complete, self.options.count, fields, function, *args, **kwargs):
                yield values
        except CallErrors, e:
            if len(e.errors) == 1 and isinstance(e.errors[0][1], FieldNotFound):
                logging.error(e.errors[0][1])
            else:
                raise

    # options related methods

    def _handle_options(self):
        self.formatter_name = self.options.formatter if self.options.formatter else 'multiline'
        self.formatter = load_formatter(self.formatter_name)

        if self.options.no_header:
            self.formatter.display_header = False

        if self.options.no_keys:
            self.formatter.display_keys = False

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
        return ['%s ' % name for name in cmd.Cmd.completenames(self, text, *ignored) if name not in self.hidden_commands]

    def completion_helper(self, text, choices):
        if text:
            return [x for x in choices if x.startswith(text)]
        else:
            return choices

    def do_backends(self, line):
        """
        backends [ACTION] [BACKEND_NAME]...

        Select used backends.

        ACTION is one of the following (default: list):
            * enable  enable given backends
            * disable disable given backends
            * only    enable given backends and disable the others
            * list    display enabled and available backends
        """
        line = line.strip()
        if line:
            args = line.split()
        else:
            args = ['list']

        action = args[0]
        given_backend_names = args[1:]

        skipped_backend_names = []
        for backend_name in given_backend_names:
            if backend_name not in [backend.name for backend in self.weboob.iter_backends()]:
                print 'Backend "%s" does not exist => skipping.' % backend_name
                skipped_backend_names.append(backend_name)
        for skipped_backend_name in skipped_backend_names:
            given_backend_names.remove(skipped_backend_name)

        if action in ('enable', 'disable', 'only'):
            if not given_backend_names:
                print 'Please give at least a backend name.'
                return

        given_backends = set(backend for backend in self.weboob.iter_backends() if backend.name in given_backend_names)

        if action == 'enable':
            action_func = self.enabled_backends.add
            for backend in given_backends:
                try:
                    action_func(backend)
                except KeyError, e:
                    print e
        elif action == 'disable':
            action_func = self.enabled_backends.remove
            for backend in given_backends:
                try:
                    action_func(backend)
                except KeyError, e:
                    logging.info('%s is not enabled' % e)
        elif action == 'only':
            self.enabled_backends = set()
            action_func = self.enabled_backends.add
            for backend in given_backends:
                try:
                    action_func(backend)
                except KeyError, e:
                    print e
        elif action == 'list':
            print 'Available: %s' % ', '.join(sorted(backend.name for backend in self.weboob.iter_backends()))
            print 'Enabled: %s' % ', '.join(sorted(backend.name for backend in self.enabled_backends))
        else:
            print 'Unknown action: "%s"' % action
            return False

    def complete_backends(self, text, line, begidx, endidx):
        choices = None
        commands = ['enable', 'disable', 'only', 'list']
        available_backends_names = set(backend.name for backend in self.weboob.iter_backends())
        enabled_backends_names = set(backend.name for backend in self.enabled_backends)

        args = line.split()
        if len(args) == 1 or len(args) == 2 and args[1] not in commands:
            choices = commands
        elif len(args) == 2 and args[1] in commands or \
                len(args) == 3 and args[1] in ('enable', 'only') and args[2] not in available_backends_names or \
                len(args) == 3 and args[1] == 'disable' and args[2] not in enabled_backends_names:
            if args[1] == 'enable':
                choices = sorted(available_backends_names - enabled_backends_names)
            elif args[1] == 'only':
                choices = sorted(available_backends_names)
            elif args[1] == 'disable':
                choices = sorted(enabled_backends_names)

        if choices is not None:
            return ['%s ' % choice for choice in choices if choice.startswith(text)] if text else choices

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

    def do_formatter(self, line):
        """
        formatter [FORMATTER_NAME | list | option OPTION_NAME [on | off]]

        If a FORMATTER_NAME is given, set the formatter to use.

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
                print ', '.join(available_formatters)
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
                if args[0] in available_formatters:
                    self.formatter = load_formatter(args[0])
                    self.formatter_name = args[0]
                else:
                    print 'Formatter "%s" is not available.\n' \
                            'Available formatters: %s.' % (args[0], ', '.join(available_formatters))
        else:
            print self.formatter_name

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
        @return  entered text by user (str)
        """

        is_bool = False

        if choices:
            question = u'%s (%s)' % (question, '/'.join(
                [s for s in (choices.iterkeys() if isinstance(choices, dict) else choices)]))
        if default is not None:
            if isinstance(default, bool):
                question = u'%s (%s/%s)' % (question, 'Y' if default else 'y', 'n' if default else 'N')
                choices = ('y', 'n', 'Y', 'N')
                default = 'y' if default else 'n'
                is_bool = True
            else:
                question = u'%s [%s]' % (question, default)

        if masked:
            question = u'(input chars are hidden) %s' % question

        question += ': '

        correct = False
        while not correct:
            line = getpass.getpass(question) if masked else raw_input(question)
            if not line and default is not None:
                line = default
            correct = (not regexp or re.match(regexp, unicode(line))) and \
                      (not choices or unicode(line) in
                       [unicode(s) for s in (choices.iterkeys() if isinstance(choices, dict) else choices)])

        if is_bool:
            return line.lower() == 'y'
        else:
            return line

    # formatting related methods

    def set_default_formatter(self, name):
        if not self.options.formatter:
            try:
                self.formatter = load_formatter(name)
            except ImportError:
                default_name = 'multiline'
                print 'Could not load default formatter "%s" for this command. Falling back to "%s".' % (
                    name, default_name)
                self.formatter = load_formatter(default_name)

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

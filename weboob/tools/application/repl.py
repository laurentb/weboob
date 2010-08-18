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

from weboob.core import CallErrors
from weboob.core.backendscfg import BackendsConfig

from .base import BackendNotFound, BaseApplication
from .formatters.load import formatters, load_formatter
from .formatters.iformatter import FieldNotFound
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
        self.weboob_commands = set(['backends', 'count', 'quit', 'select'])
        self.hidden_commands = set(['EOF'])

        option_parser = OptionParser(self.SYNOPSIS, version=self._get_optparse_version())
        app_options = OptionGroup(option_parser, '%s Options' % self.APPNAME.capitalize())
        self.add_application_options(app_options)
        option_parser.add_option_group(app_options)

        try:
            BaseApplication.__init__(self, option_parser=option_parser)
        except BackendsConfig.WrongPermissions, e:
            logging.error(u'Error: %s' % e)
            sys.exit(1)

        self._parser.format_description = lambda x: self._parser.description

        if self._parser.description is None:
            self._parser.description = ''
        help_str = self.do_help(return_only=True)
        self._parser.description += help_str

        results_options = OptionGroup(self._parser, 'Results Options')
        results_options.add_option('-c', '--condition', help='filter result items to display given a boolean condition')
        results_options.add_option('-n', '--count', default='10', type='int',
                                   help='get a maximum number of results (all backends merged)')
        results_options.add_option('-s', '--select', help='select result item keys to display (comma separated)')
        self._parser.add_option_group(results_options)

        formatting_options = OptionGroup(self._parser, 'Formatting Options')
        formatting_options.add_option('-f', '--formatter', choices=formatters,
                                      help='select output formatter (%s)' % u','.join(formatters))
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
            self.cmdloop()

    def do(self, function, *args, **kwargs):
        """
        Call Weboob.do(), passing count and selected fields given by user.
        """
        if kwargs.pop('backends', None) is None:
            kwargs['backends'] = self.enabled_backends
        return self.weboob.do(self._complete, self.options.count, self.selected_fields, function, *args, **kwargs)

    # options related methods

    def _handle_options(self):
        if self.options.formatter:
            formatter_name = self.options.formatter
        else:
            formatter_name = 'multiline'
        self.formatter = load_formatter(formatter_name)

        if self.options.no_header:
            self.formatter.display_header = False

        if self.options.no_keys:
            self.formatter.display_keys = False

        if self.options.select:
            self.selected_fields = self.options.select.split(',')
        else:
            self.selected_fields = 'direct'

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

    def do_help(self, arg=None, return_only=False):
        if return_only:
            stringio = StringIO()
            old_stdout = self.stdout
            self.stdout = stringio
        if arg:
            cmd_names = set(name[3:] for name in self.get_names() if name.startswith('do_'))
            if arg in cmd_names:
                command_help = self.get_command_help(arg)
                if command_help is None:
                    logging.warning(u'Command "%s" is undocumented' % arg)
                else:
                    self.stdout.write('%s\n' % command_help)
            else:
                logging.error(u'Unknown command: "%s"' % arg)
        else:
            names = set(name for name in self.get_names() if name.startswith('do_'))
            application_cmds_doc = []
            weboob_cmds_doc = []
            cmds_undoc = []
            for name in sorted(names):
                cmd = name[3:]
                if cmd in self.hidden_commands.union(['help']):
                    continue
                elif getattr(self, name).__doc__:
                    short_help = '    %s' % self.get_command_help(cmd, short=True)
                    if cmd in self.weboob_commands:
                        weboob_cmds_doc.append(short_help)
                    else:
                        application_cmds_doc.append(short_help)
                else:
                    cmds_undoc.append(cmd)
            application_cmds_header = '%s commands' % self.APPNAME.capitalize()
            self.stdout.write('%s\n%s\n' % (application_cmds_header, '-' * len(application_cmds_header)))
            self.stdout.write('\n'.join(application_cmds_doc) + '\n\n')
            weboob_cmds_header = 'Generic Weboob commands'
            self.stdout.write('%s\n%s\n' % (weboob_cmds_header, '-' * len(weboob_cmds_header)))
            self.stdout.write('\n'.join(weboob_cmds_doc) + '\n\n')
            self.print_topics(self.undoc_header, cmds_undoc, 15,80)
            self.stdout.write('Type "help <command>" for more info about a command.\n')
        if return_only:
            self.stdout = old_stdout
            return stringio.getvalue()

    def emptyline(self):
        """
        By default, an emptyline repeats the previous command.
        Overriding this function disables this behaviour.
        """
        pass

    def default(self, line):
        logging.error(u'Unknown command: "%s"' % line)

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
        if not line:
            args = ['list']
        else:
            args = line.split()

        action = args[0]
        given_backend_names = args[1:]

        if action in ('enable', 'disable', 'only'):
            if not given_backend_names:
                logging.error(u'Please give at least a backend name.')

        given_backends = set(backend for backend in self.weboob.iter_backends() if backend.name in given_backend_names)

        if action == 'enable':
            action_func = self.enabled_backends.add
            for backend in given_backends:
                try:
                    action_func(backend)
                except KeyError, e:
                    logging.error(e)
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
                    logging.error(e)
        elif action == 'list':
            print 'Available: %s' % ', '.join(sorted(backend.name for backend in self.weboob.iter_backends()))
            print 'Enabled: %s' % ', '.join(sorted(backend.name for backend in self.enabled_backends))
        else:
            logging.error(u'Unknown action: "%s"' % action)
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
            if args[1] in ('enable', 'only'):
                choices = sorted(available_backends_names - enabled_backends_names)
            elif args[1] == 'disable':
                choices = sorted(enabled_backends_names)

        if choices is not None:
            return ['%s ' % choice for choice in choices if choice.startswith(text)] if text else choices

    def do_count(self, line):
        """
        count [NUMBER]

        If an argument is given, set the maximum number of results fetched.
        Otherwise, display the current setting.

        Count must be at least 1, or negative for infinite.
        """
        if line:
            try:
                self.options.count = int(line)
            except ValueError, e:
                print e
            if self.options.count == 0:
                print 'count must be at least 1, or negative for infinite'
            elif self.options.count < 0:
                self.options.count = None
        else:
            print self.options.count

    def do_select(self, line):
        """
        select [FIELD_NAME]... | "direct" | "full"
        """
        print self.selected_fields


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
                logging.error('Could not load default formatter "%s" for this command. Falling back to "%s".' % (
                    name, default_name))
                self.formatter = load_formatter(default_name)

    def set_formatter_header(self, string):
        self.formatter.set_header(string)

    def format(self, result):
        try:
            self.formatter.format(obj=result, selected_fields=self.selected_fields, condition=self.condition)
        except FieldNotFound, e:
            logging.error(e)
        except ResultsConditionException, e:
            logging.error(e)

    def parse_id(self, _id):
        try:
            _id, backend_name = _id.rsplit('@', 1)
        except ValueError:
            backend_name = None
        return _id, backend_name

# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon, Julien Hébert, Christophe Benz

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

import logging
import sys, tty, termios
import re
from inspect import getargspec
from functools import partial

import weboob
from weboob.modules import BackendsConfig

from .base import BaseApplication
from .formatters import formatters_classes
from .results import Results, WhereCondition, WhereConditionException


__all__ = ['ConsoleApplication']


class ConsoleApplication(BaseApplication):
    SYNOPSIS = 'Usage: %prog [options (-h for help)] command [parameters...]'

    def __init__(self):
        try:
            BaseApplication.__init__(self)
        except BackendsConfig.WrongPermissions, e:
            logging.error(u'Error: %s' % e)
            sys.exit(1)

        self._parser.format_description = lambda x: self._parser.description

        if self._parser.description is None:
            self._parser.description = ''
        self._parser.description += 'Available commands:\n'
        for name, arguments, doc_string in self._commands:
            command = '%s %s' % (name, arguments)
            self._parser.description += '   %-30s %s\n' % (command, doc_string)

        self._parser.add_option('-f', '--formatter', default='simple', choices=formatters_classes.keys(),
                help='select output formatter (%s)' % u','.join(formatters_classes.keys()))
        self._parser.add_option('-s', '--select', help='select result item key(s) to display (comma-separated)')
        self._parser.add_option('-w', '--where', help='filter results to display with boolean condition')

    def _handle_app_options(self):
        self._formatter = formatters_classes[self.options.formatter]

        if self.options.select:
            self.selected_fields = self.options.select.split(',')
        else:
            self.selected_fields = None

        if self.options.where:
            self.where_condition = WhereCondition(self.options.where)
        else:
            self.where_condition = None

    def _get_completions(self):
        return set(name for name, arguments, doc_string in self._commands)

    def ask(self, question, default=None, masked=False, regexp=None):
        """
        Ask a question to user.

        @param question  text displayed (str)
        @param default  optional default value (str)
        @param masked  if True, do not show typed text (bool)
        @param regexp  text must match this regexp (str)
        @return  entered text by user (str)
        """

        correct = False

        if not default is None:
            question = '%s [%s]' % (question, default)

        while not correct:
            sys.stdout.write('%s: ' % (question))

            if masked:
                attr = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin)

            line = sys.stdin.readline().split('\n')[0]

            if not line and not default is None:
                line = default

            if masked:
                termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, attr)
                sys.stdout.write('\n')

            correct = not regexp or re.match(regexp, str(line))

        return line

    def process_command(self, command=None, *args):
        if command is None:
            self._parser.print_help()
            return 0

        def f(x):
            return x.startswith('command_' + command)

        matching_commands = filter(f, dir(self))

        if len(matching_commands) == 0:
            sys.stderr.write("No such command: %s.\n" % command)
            return 1
        if len(matching_commands) != 1:
            sys.stderr.write("Ambiguious command %s: %s.\n" % (command, ', '.join(
                [s.replace('command_', '', 1) for s in matching_commands])))
            return 1

        func = getattr(self, matching_commands[0])

        _args, varargs, varkw, defaults = getargspec(func)
        nb_max_args = nb_min_args = len(_args) - 1
        if defaults:
            nb_min_args -= len(defaults)

        if len(args) > nb_max_args and not varargs:
            sys.stderr.write("Command '%s' takes at most %d arguments.\n" % (command, nb_max_args))
            return 1
        if len(args) < nb_min_args:
            if varargs or defaults:
                sys.stderr.write("Command '%s' takes at least %d arguments.\n" % (command, nb_min_args))
            else:
                sys.stderr.write("Command '%s' takes %d arguments.\n" % (command, nb_min_args))
            return 1

        try:
            command_result = func(*args)
        except weboob.CallErrors, errors:
            logging.error(errors)
            return 1

        # Process result
        if isinstance(command_result, Results):
            self.format(command_result)
            return 0
        elif isinstance(command_result, (str, unicode)):
            print command_result
            return 0
        elif isinstance(command_result, int):
            return command_result
        elif command_result is None:
            return 0
        else:
            try:
                print unicode(command_result)
            except ValueError:
                raise Exception('command_result type not expected: %s' % type(command_result))

    _commands = []
    def register_command(f, doc_string, register_to=_commands):
        def get_arguments(func, skip=0):
            """
            Get arguments of a function as a string.
            skip is the number of skipped arguments.
            """
            skip += 1
            args, varargs, varkw, defaults = getargspec(func)
            cut = len(args)
            if defaults:
                cut -= len(defaults)
            args = ["<%s>" % a for a in args[skip:cut]] + \
                   ["[%s]" % a for a in args[cut:]]
            if varargs:
                args.append("[%s..]" % varargs)
            if varkw:
                args.append("{WTF}" % varkw)
            return " ".join(args)

        command_name = f.func_name.replace('command_', '')
        register_to.append((command_name, get_arguments(f), doc_string))
        return f

    def command(doc_string, f=register_command):
        return partial(f, doc_string=doc_string)

    def format(self, result):
        try:
            result = self._formatter.format(result, selected_fields=self.selected_fields, where_condition=self.where_condition)
            if result is not None:
                print result
        except WhereConditionException, e:
            logging.error(e)

    register_command = staticmethod(register_command)
    command = staticmethod(command)

    def load_backends(self, caps=None, names=None, *args, **kwargs):
        loaded_backends = BaseApplication.load_backends(self, caps, names, *args, **kwargs)
        if not loaded_backends:
            logging.error(u'Cannot start application: no configured backend was found.\nHere is a list of all available backends:')
            from weboob.frontends.weboobcfg import WeboobCfg
            weboobcfg = WeboobCfg()
            if caps is not None:
                if not isinstance(caps, (list, tuple, set)):
                    caps = (caps,)
                caps = iter(cap.__name__ for cap in caps)
            weboobcfg.command_modules(*caps)
            logging.error(u'You can configure a backends using the "weboobcfg add" command:\nweboobcfg add <name> [options..]')
            sys.exit(0)

# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Julien Hébert, Christophe Benz
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

from functools import partial
import getpass
from inspect import getargspec
import logging
from optparse import OptionGroup, OptionParser
import re
import sys

from weboob.core import CallErrors
from weboob.core.backends import BackendsConfig

from .base import BackendNotFound, BaseApplication
from .formatters.load import formatters, load_formatter
from .results import ResultsCondition, ResultsConditionException


__all__ = ['ConsoleApplication']


class ConsoleApplication(BaseApplication):
    SYNOPSIS = 'Usage: %prog [options (-h for help)] command [parameters...]'

    def __init__(self):
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
        self._parser.description += 'Available commands:\n'
        for name, arguments, doc_string in self._commands:
            command = '%s %s' % (name, arguments)
            self._parser.description += '   %-30s %s\n' % (command, doc_string)

        results_options = OptionGroup(self._parser, 'Results Options')
        results_options.add_option('-c', '--condition', help='filter result items to display given a boolean condition')
        results_options.add_option('-f', '--formatter', choices=formatters, help='select output formatter (%s)' % u','.join(formatters))
        results_options.add_option('-s', '--select', help='select result item key(s) to display (comma-separated)')
        self._parser.add_option_group(results_options)

        formatting_options = OptionGroup(self._parser, 'Formatting Options')
        formatting_options.add_option('--no-header', dest='no_header', action='store_true', help='display only objects fields')
        self._parser.add_option_group(formatting_options)

    def add_application_options(self, group):
        pass

    def _handle_app_options(self):
        if self.options.formatter:
            formatter_name = self.options.formatter
        else:
            formatter_name = 'multiline'
        self.formatter = load_formatter(formatter_name)

        if self.options.no_header:
            self.formatter.display_header = False

        if self.options.select:
            self.selected_fields = self.options.select.split(',')
            if '*' not in self.selected_fields:
                self.formatter.display_keys = False
        else:
            self.selected_fields = None

        if self.options.condition:
            self.condition = ResultsCondition(self.options.condition)
        else:
            self.condition = None

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

        if default is not None:
            question = u'%s [%s]' % (question, default)
        hidden_msg = u'(input chars are hidden) ' if masked else ''
        question = u'%s%s: ' % (hidden_msg, question)

        correct = False
        while not correct:
            line = getpass.getpass(question) if masked else raw_input(question)
            if not line and default is not None:
                line = default
            correct = not regexp or re.match(regexp, unicode(line))

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
        except CallErrors, errors:
            logging.error(errors)
            return 1

        self.formatter.flush()

        # Process result if value is returned by command
        if isinstance(command_result, str):
            print command_result
        elif isinstance(command_result, unicode):
            print command_result.encode('utf-8')
        elif isinstance(command_result, int):
            return command_result
        elif command_result is None:
            return 0
        else:
            try:
                print unicode(command_result).encode('utf-8')
            except ValueError:
                raise Exception(u'Command result type not expected: %s' % type(command_result))

        return 0

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

    def set_default_formatter(self, name):
        if not self.options.formatter:
            self.formatter = load_formatter(name)

    def set_formatter_header(self, string):
        self.formatter.set_header(string)

    def format(self, result, backend_name=None):
        try:
            self.formatter.format(obj=result, backend_name=backend_name,
                                  selected_fields=self.selected_fields, condition=self.condition)
        except ResultsConditionException, e:
            logging.error(e)

    register_command = staticmethod(register_command)
    command = staticmethod(command)

    def load_backends(self, caps=None, names=None, *args, **kwargs):
        loaded_backends = BaseApplication.load_backends(self, caps, names, *args, **kwargs)
        if not loaded_backends:
            logging.error(u'Cannot start application: no configured backend was found.\nHere is a list of all available backends:')
            from weboob.applications.weboobcfg import WeboobCfg
            weboobcfg = WeboobCfg()
            if caps is not None:
                if not isinstance(caps, (list, tuple, set)):
                    caps = (caps,)
                caps = iter(cap.__name__ for cap in caps)
            weboobcfg.command_modules(*caps)
            logging.error(u'You can configure a backends using the "weboobcfg add" command:\nweboobcfg add <name> [options..]')
            sys.exit(0)

    def parse_id(self, _id):
        try:
            _id, backend_name = _id.rsplit('@', 1)
        except ValueError:
            backend_name = None
        return _id, backend_name

    @classmethod
    def run(klass, args=None):
        try:
            super(ConsoleApplication, klass).run(args)
        except BackendNotFound, e:
            logging.error(e)

    def do(self, function, *args, **kwargs):
        kwargs['required_fields'] = self.options.select
        return self.weboob.do(function, *args, **kwargs)

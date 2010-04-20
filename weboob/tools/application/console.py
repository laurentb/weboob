# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon, Julien Hébert

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

from weboob.modules import BackendsConfig

from .base import BaseApplication


__all__ = ['ConsoleApplication']


class TableFormatter(object):
    @classmethod
    def format(klass, data):
        from prettytable import PrettyTable
        formatted = u''
        before = data.get('BEFORE')
        if before is not None:
            formatted += u'%s\n' % before
            del data['BEFORE']
        header = data.get('HEADER')
        if header is not None:
            del data['HEADER']
        for backend_name, result in data.iteritems():
            if not result:
                continue
            if header is None:
                header = ['' for e in xrange(len(result[0]))]
            table = PrettyTable(list(header))
            for col in header:
                table.set_field_align(col, 'l')
            for row in result:
                table.add_row(row)
            formatted += u'%s\n%s\n' % (backend_name, unicode(table))
        return unicode(formatted).strip()


class TextFormatter(object):
    @classmethod
    def format(klass, data):
        formatted = u''
        before = data.get('BEFORE')
        if before is not None:
            formatted += u'%s\n' % before
            del data['BEFORE']
        header = data.get('HEADER')
        if header is not None:
            del data['HEADER']
        for backend_name, result in data.iteritems():
            if not result:
                continue
            if header is None:
                header = ['' for e in xrange(len(result[0]))]
            formatted += u'%s\n%s\n' % (backend_name, '=' * len(backend_name))
            for row in result:
                formatted_cols = []
                for i, col in enumerate(row):
                    if header[i]:
                        formatted_cols.append(u'%s: %s' % (header[i], col))
                    else:
                        formatted_cols.append(unicode(col))
                formatted += u'%s\n' % u' '.join(formatted_cols)
        return unicode(formatted).strip()


formatters = {'text':  TextFormatter,
              'table': TableFormatter,
             }


class ConsoleApplication(BaseApplication):
    SYNOPSIS = 'Usage: %prog [options (-h for help)] command [parameters...]'

    def __init__(self):
        try:
            BaseApplication.__init__(self)
        except BackendsConfig.WrongPermissions, e:
            print >>sys.stderr, 'Error: %s' % e.message
            sys.exit(1)
        self.default_output_format = None

    def _configure_parser(self, parser):
        parser.format_description = lambda x: parser.description

        if parser.description is None:
            parser.description = ''
        parser.description += 'Available commands:\n'
        for f in self._command_help:
            parser.description += '   %s\n' % f

        parser.add_option('-o', '--output-format', choices=formatters.keys(),
                          help='output format %s (default: table)' % formatters.keys())

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

    def process_command(self, command='help', *args):
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

        command_result = func(*args)

        # Process result
        if isinstance(command_result, dict):
            if self.options.output_format is not None:
                output_format = self.options.output_format
            else:
                if self.default_output_format is not None:
                    output_format = self.default_output_format
                else:
                    output_format = 'table'
            try:
                print formatters[output_format].format(command_result)
            except ImportError, e:
                logging.error(u'Could not use formatter "%s". Error: %s' % (output_format, e.message))
            return 0
        elif isinstance(command_result, int):
            return command_result
        elif command_result is None:
            return 0
        else:
            raise Exception('Should never go here')

    _command_help = []
    def register_command(f, doc_string, register_to=_command_help):
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
        command = '%s %s' % (command_name, get_arguments(f))
        register_to.append('%-30s %s' % (command, doc_string))
        return f

    def command(doc_string, f=register_command):
        return partial(f, doc_string=doc_string)

    @command("display this notice")
    def command_help(self):
        sys.stdout.write("Available commands:\n")
        for f in self._command_help:
            sys.stdout.write('   %s\n' % f)

    register_command = staticmethod(register_command)
    command = staticmethod(command)

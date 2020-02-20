#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright(C) 2010-2018 Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function

import imp
import inspect
import optparse
import os
import re
import sys
import time
from datetime import datetime
from textwrap import dedent

from weboob.tools.application.base import Application

BASE_PATH = os.path.join(os.path.dirname(__file__), os.pardir)
DEST_DIR = 'man'
COMP_PATH = 'tools/weboob_bash_completion'


class ManpageHelpFormatter(optparse.HelpFormatter):
    def __init__(self,
                 app,
                 indent_increment=0,
                 max_help_position=0,
                 width=80,
                 short_first=1):
        optparse.HelpFormatter.__init__(self, indent_increment, max_help_position, width, short_first)
        self.app = app

    def format_heading(self, heading):
        return ".SH %s\n" % heading.upper()

    def format_usage(self, usage):
        txt = ''
        for line in usage.split('\n'):
            line = line.lstrip().split(' ', 1)
            if len(txt) > 0:
                txt += '.br\n'
            txt += '.B %s\n' % line[0]

            arg_re = re.compile(r'([\[\s])([\w_]+)')
            args = re.sub(arg_re, r"\1\\fI\2\\fR", line[1])
            txt += args
            txt += '\n'
        return '.SH SYNOPSIS\n%s' % txt

    def format_description(self, description):
        desc = u'.SH DESCRIPTION\n.LP\n\n%s\n' % description
        if hasattr(self.app, 'CAPS'):
            self.app.weboob.modules_loader.load_all()
            caps = self.app.CAPS if isinstance(self.app.CAPS, tuple) else (self.app.CAPS,)
            modules = []
            for name, module in self.app.weboob.modules_loader.loaded.items():
                if module.has_caps(*caps):
                    modules.append(u'* %s (%s)' % (name, module.description))
            if len(modules) > 0:
                desc += u'\n.SS Supported websites:\n'
                desc += u'\n.br\n'.join(sorted(modules))
        return desc

    def format_commands(self, commands):
        s = u''
        for section, cmds in commands.items():
            if len(cmds) == 0:
                continue
            s += '.SH %s COMMANDS\n' % section.upper()
            for cmd in sorted(cmds):
                s += '.TP\n'
                h = cmd.split('\n')
                if ' ' in h[0]:
                    cmdname, args = h[0].split(' ', 1)
                    arg_re = re.compile(r'([A-Z_]+)')
                    args = re.sub(arg_re, r"\\fI\1\\fR", args)

                    s += '\\fB%s\\fR %s' % (cmdname, args)
                else:
                    s += '\\fB%s\\fR' % h[0]
                s += '%s\n' % '\n.br\n'.join(h[1:])
        return s

    def format_option_strings(self, option):
        opts = optparse.HelpFormatter.format_option_strings(self, option).split(", ")

        return ".TP\n" + ", ".join("\\fB%s\\fR" % opt for opt in opts)


def main():
    scripts_path = os.path.join(BASE_PATH, 'weboob', 'applications')
    files = os.listdir(scripts_path)
    completions = dict()

    for fname in files:
        fpath = os.path.join(scripts_path, fname)
        if os.path.isdir(fpath) and not fname.startswith('_'):
            try:
                fp, pathname, description = imp.find_module(fname, [scripts_path])
                module = imp.load_module(fname, fp, pathname, description)
            except OSError as e:
                print("Unable to load the %s application (%s)"
                      % (fname, e), file=sys.stderr)
            else:
                print("Loaded %s" % fname)
                # Find the applications we can handle
                for klass in module.__dict__.values():
                    if inspect.isclass(klass) and issubclass(klass, Application) and klass.VERSION:
                        completions[klass.APPNAME] = analyze_application(klass, klass.APPNAME)

    write_completions(completions)


def format_title(title):
    return re.sub(r'^(.+):$', r'.SH \1\n.TP', title.group().upper())


# XXX useful because the PyQt QApplication destructor crashes sometimes. By
# keeping every applications until program end, it prevents to stop before
# every manpages have been generated. If it crashes at exit, it's not a
# really a problem.
applications = []


def analyze_application(app, script_name):
    application = app()
    applications.append(application)

    formatter = ManpageHelpFormatter(application)

    # patch the application
    application._parser.prog = "%s" % script_name
    application._parser.formatter = formatter
    helptext = application._parser.format_help(formatter)

    cmd_re = re.compile(r'^.+ Commands:$', re.MULTILINE)
    helptext = re.sub(cmd_re, format_title, helptext)
    helptext = helptext.replace("-", r"\-")
    coding = r'.\" -*- coding: utf-8 -*-'
    comment = r'.\" This file was generated automatically by tools/make_man.sh.'
    header = '.TH %s 1 "%s" "%s %s"' % (script_name.upper(), time.strftime("%d %B %Y"),
                                        script_name, app.VERSION.replace('.', '\\&.'))
    name = ".SH NAME\n%s \- %s" % (script_name, application.SHORT_DESCRIPTION)
    condition = """.SH CONDITION
The \-c and \-\-condition is a flexible way to filter and get only interesting results. It supports conditions on numerical values, dates, durations and strings. Dates are given in YYYY\-MM\-DD or YYYY\-MM\-DD HH:MM format. Durations look like XhYmZs where X, Y and Z are integers. Any of them may be omitted. For instance, YmZs, XhZs or Ym are accepted.
The syntax of one expression is "\\fBfield operator value\\fR". The field to test is always the left member of the expression.
.LP
The field is a member of the objects returned by the command. For example, a bank account has "balance", "coming" or "label" fields.
.SS The following operators are supported:
.TP
=
Test if object.field is equal to the value.
.TP
!=
Test if object.field is not equal to the value.
.TP
>
Test if object.field is greater than the value. If object.field is date, return true if value is before that object.field.
.TP
<
Test if object.field is less than the value. If object.field is date, return true if value is after that object.field.
.TP
|
This operator is available only for string fields. It works like the Unix standard \\fBgrep\\fR command, and returns True if the pattern specified in the value is in object.field.
.SS Expression combination
.LP
You can make a expression combinations with the keywords \\fB" AND "\\fR, \\fB" OR "\\fR an \\fB" LIMIT "\\fR.
.LP
The \\fBLIMIT\\fR keyword can be used to limit the number of items upon which running the expression. \\fBLIMIT\\fR can only be placed at the end of the expression followed by the number of elements you want.
.SS Examples:
.nf
.B boobank ls \-\-condition 'label=Livret A'
.fi
Display only the "Livret A" account.
.PP
.nf
.B boobank ls \-\-condition 'balance>10000'
.fi
Display accounts with a lot of money.
.PP
.nf
.B boobank history account@backend \-\-condition 'label|rewe'
.fi
Get transactions containing "rewe".
.PP
.nf
.B boobank history account@backend \-\-condition 'date>2013\-12\-01 AND date<2013\-12\-09'
.fi
Get transactions betweens the 2th December and 8th December 2013.
.PP
.nf
.B boobank history account@backend \-\-condition 'date>2013\-12\-01  LIMIT 10'
.fi
Get transactions after the 2th December in the last 10 transactions
"""
    footer = """.SH COPYRIGHT
%s
.LP
For full copyright information see the COPYING file in the weboob package.
.LP
.RE
.SH FILES
 "~/.config/weboob/backends" """ % application.COPYRIGHT.replace('YEAR', '%d' % datetime.today().year)
    if len(app.CONFIG) > 0:
        footer += '\n\n "~/.config/weboob/%s"' % app.APPNAME

    # Skip internal applications.
    footer += "\n\n.SH SEE ALSO\nHome page: http://weboob.org/applications/%s" % application.APPNAME

    mantext = u"%s\n%s\n%s\n%s\n%s\n%s\n%s" % (coding, comment, header, name, helptext, condition, footer)
    with open(os.path.join(BASE_PATH, DEST_DIR, "%s.1" % script_name), 'w+') as manfile:
        for line in mantext.split('\n'):
            manfile.write('%s\n' % line.lstrip())
    print("wrote %s/%s.1" % (DEST_DIR, script_name))

    return application._shell_completion_items()


def write_completions(completions):
    compscript = dedent('''
    # Weboob completion for Bash (automatically generated by tools/make_man.sh)
    #
    # vim: filetype=sh expandtab softtabstop=4 shiftwidth=4
    #
    # This file is part of weboob.
    #
    # This script can be distributed under the same license as the
    # weboob or bash packages.
    ''')
    for name, items in completions.items():
        compscript += dedent('''
        _weboob_{1}()
        {{
            local cur args

            COMPREPLY=()
            cur=${{COMP_WORDS[COMP_CWORD]}}
            args="{2}"

            COMPREPLY=( $(compgen -o default -W "${{args}}" -- "$cur" ) )
        }}
        complete -F _weboob_{1} {0}
        ''').format(name, name.replace('-', '_'), ' '.join(items))
    with open(os.path.join(BASE_PATH, COMP_PATH), 'w') as f:
        f.write(compscript)


if __name__ == '__main__':
    sys.exit(main())

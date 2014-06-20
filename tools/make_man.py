#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Laurent Bachelier
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

import sys
import os
import tempfile
import imp
import inspect
import optparse
import re
import time

from weboob.tools.application.base import BaseApplication

BASE_PATH = os.path.join(os.path.dirname(__file__), os.pardir)
DEST_DIR = 'man'


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
            backends = []
            for name, backend in self.app.weboob.modules_loader.loaded.iteritems():
                if backend.has_caps(self.app.CAPS):
                    backends.append(u'* %s (%s)' % (name, backend.description))
            if len(backends) > 0:
                desc += u'\n.SS Supported websites:\n'
                desc += u'\n.br\n'.join(sorted(backends))
        return desc

    def format_commands(self, commands):
        s = u''
        for section, cmds in commands.iteritems():
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
    scripts_path = os.path.join(BASE_PATH, "scripts")
    files = os.listdir(scripts_path)

    # Create a fake "scripts" modules to import the scripts into
    sys.modules["scripts"] = imp.new_module("scripts")

    for fname in files:
        fpath = os.path.join(scripts_path, fname)
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            with open(fpath) as f:
                # Python will likely want create a compiled file, we provide a place
                tmpdir = os.path.join(tempfile.gettempdir(), "weboob", "make_man")
                if not os.path.isdir(tmpdir):
                    os.makedirs(tmpdir)
                tmpfile = os.path.join(tmpdir, fname)

                desc = ("", "U", imp.PY_SOURCE)
                try:
                    script = imp.load_module("scripts.%s" % fname, f, tmpfile, desc)
                except ImportError as e:
                    print >>sys.stderr, "Unable to load the %s script (%s)" \
                        % (fname, e)
                else:
                    print "Loaded %s" % fname
                    # Find the applications we can handle
                    for klass in script.__dict__.itervalues():
                        if inspect.isclass(klass) and issubclass(klass, BaseApplication):
                            analyze_application(klass, fname)
                finally:
                    # Cleanup compiled files if needed
                    if (os.path.isfile(tmpfile + "c")):
                        os.unlink(tmpfile + "c")


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
The \-c and \-\-condition is a flexible way to sort and get only interesting results. It supports conditions on numerical values, dates, and strings. Dates are given in YYYY\-MM\-DD format.
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
You can make a expression combinations with the keywords \\fB" AND "\\fR and \\fB" OR "\\fR.

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
"""
    footer = """.SH COPYRIGHT
%s
.LP
For full COPYRIGHT see COPYING file with weboob package.
.LP
.RE
.SH FILES
 "~/.config/weboob/backends" """ % application.COPYRIGHT
    if len(app.CONFIG) > 0:
        footer += '\n\n "~/.config/weboob/%s"' % app.APPNAME

    # Skip internal applications.
    footer += "\n\n.SH SEE ALSO\nHome page: http://weboob.org/applications/%s" % application.APPNAME

    mantext = u"%s\n%s\n%s\n%s\n%s\n%s\n%s" % (coding, comment, header, name, helptext, condition, footer)
    with open(os.path.join(BASE_PATH, DEST_DIR, "%s.1" % script_name), 'w+') as manfile:
        for line in mantext.split('\n'):
            manfile.write('%s\n' % line.lstrip().encode('utf-8'))
    print "wrote %s/%s.1" % (DEST_DIR, script_name)

if __name__ == '__main__':
    sys.exit(main())

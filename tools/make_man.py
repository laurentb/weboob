#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2010  Laurent Bachelier
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

import sys, os, tempfile
import imp, inspect
import optparse
import re
import time

from weboob.tools.application.base import BaseApplication

BASE_PATH = os.path.join(os.path.dirname(__file__), os.pardir)

class ManpageHelpFormatter(optparse.HelpFormatter):
    def __init__ (self,
            indent_increment=0,
            max_help_position=0,
            width=80,
            short_first=1):
        optparse.HelpFormatter.__init__(self, indent_increment, max_help_position, width, short_first)

    def format_heading(self, heading):
        return ".SH %s\n" % heading.upper()

    def format_option_strings(self, option):
        opts = optparse.HelpFormatter.format_option_strings(self, option).split(", ")

        return ".TP\n"+", ".join(["\\fB%s\\fR" % opt for opt in opts])


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
                tmpdir = os.path.join(tempfile.gettempdir(), \
                        "weboob", "make_man")
                if not os.path.isdir(tmpdir):
                    os.makedirs(tmpdir)
                tmpfile = os.path.join(tmpdir, fname)

                desc = ("", "U", imp.PY_SOURCE)
                try:
                    script = imp.load_module("scripts.%s" % fname, f, tmpfile, desc)
                except ImportError, e:
                    print >> sys.stderr, "Unable to load the %s script (%s)" \
                        % (fname, e)
                else:
                    print "Loaded %s" % fname
                    # Find the applications we can handle
                    for klass in script.__dict__.itervalues():
                        if inspect.isclass(klass) and issubclass(klass, BaseApplication):
                            analyze_application(klass, fname)
                finally:
                    # Cleanup compiled files if needed
                    if (os.path.isfile(tmpfile+"c")):
                        os.unlink(tmpfile+"c")

def format_title(title):
    return re.sub(r'^(.+):$', r'.SH \1\n.TP', title.group().upper())

def analyze_application(app, script_name):
    formatter = ManpageHelpFormatter()
    application = app()

    # patch the application
    application._parser.prog = ".B %s\n" % script_name
    helptext = application._parser.format_help(formatter)

    cmd_re = re.compile(r'^.+ Commands:$', re.MULTILINE)
    helptext = re.sub(cmd_re, format_title, helptext)
    usg_re = re.compile(r'^\s*Usage:\s+', re.MULTILINE)
    helptext = re.sub(usg_re, ".SH SYNOPSIS\n", helptext)
    helptext = helptext.replace("-", r"\-")
    header = '.TH %s 1 "%s"' % (script_name.upper(), time.strftime("%d %B %Y").upper())
    name = ".SH NAME\n%s" % script_name
    mantext = "%s\n%s\n%s" % (header, name, helptext)
    with open(os.path.join(BASE_PATH, "man2", "%s.1" % script_name), 'w+') as manfile:
        manfile.write(mantext)
    print "wrote man2/%s.1" % script_name

if __name__ == '__main__':
    sys.exit(main())

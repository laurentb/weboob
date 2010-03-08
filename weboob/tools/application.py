#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ft=python et softtabstop=4 cinoptions=4 shiftwidth=4 ts=4 ai

"""
Copyright(C) 2010  Romain Bignon

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

import sys, tty, termios
import re

from weboob import Weboob

class BaseApplication(object):
    APPNAME = ''
    CONFIG = {}

    def __init__(self):
        self.weboob = Weboob(self.APPNAME)
        self.config = self.weboob.getFrontendConfig(self.CONFIG)

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



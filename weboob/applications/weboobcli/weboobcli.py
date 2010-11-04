# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


import sys

from weboob.tools.application.repl import ReplApplication


__all__ = ['WeboobCli']


class WeboobCli(ReplApplication):
    APPNAME = 'weboob-cli'
    VERSION = '0.3.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    SYNOPSIS =  'Usage: %prog [-dqv] [-b backends] [-cnfs] capability method [arguments..]\n'
    SYNOPSIS += '       %prog [--help] [--version]'
    DISABLE_REPL = True

    def load_default_backends(self):
        pass

    def main(self, argv):
        if len(argv) < 3:
            print >>sys.stderr, "Syntax: %s capability method [args ..]" % argv[0]
            return 1

        cap_s = argv[1]
        cmd = argv[2]
        args = argv[3:]

        self.load_backends(cap_s)

        for backend, obj in self.do(cmd, *args):
            self.format(obj)

        return 0

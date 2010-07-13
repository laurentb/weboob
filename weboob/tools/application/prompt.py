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

from weboob.core.ouiboube import Weboob
from weboob.core.scheduler import Scheduler

from .console import ConsoleApplication


__all__ = ['PromptApplication']


class PromptScheduler(Scheduler):
    def __init__(self, prompt_cb, read_cb):
        Scheduler.__init__(self)
        self.read_cb = read_cb
        self.prompt_cb = prompt_cb

    def run(self):
        try:
            while not self.stop_event.isSet():
                self.prompt_cb()
                line = sys.stdin.readline()
                if not line:
                    self.want_stop()
                    sys.stdout.write('\n')
                else:
                    self.read_cb(line.strip())
        except KeyboardInterrupt:
            self._wait_to_stop()
            sys.stdout.write('\n')
        else:
            self._wait_to_stop()
        return True

class PromptApplication(ConsoleApplication):
    SYNOPSIS = 'Usage: %prog [options (-h for help)]'

    def create_weboob(self):
        return Weboob(scheduler=PromptScheduler(self.prompt, self.read_cb))

    @ConsoleApplication.command("Display this notice")
    def command_help(self):
        print 'Available commands:'
        for name, arguments, doc_string in self._commands:
            command = '%s %s' % (name, arguments)
            print '   %-30s %s' % (command, doc_string)

    def prompt(self):
        sys.stdout.write('> ')
        sys.stdout.flush()

    def loop(self):
        self.weboob.loop()

    def read_cb(self, line):
        line = line.split()
        if line:
            self.process_command(*line)

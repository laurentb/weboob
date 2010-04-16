# -*- coding: utf-8 -*-

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

import sched
import time
import select
import sys

from weboob import Weboob
from weboob.scheduler import Scheduler

from .console import ConsoleApplication


__all__ = ['PromptApplication']


class PromptScheduler(Scheduler):
    def __init__(self, prompt_cb, read_cb):
        self.scheduler = sched.scheduler(time.time, self.sleep)
        self.read_cb = read_cb
        self.prompt_cb = prompt_cb

    def sleep(self, d):
        self.prompt_cb()
        try:
            read, write, excepts = select.select([sys.stdin], [], [], d or None)
            if read:
                line = sys.stdin.readline()
                if not line:
                    self.want_stop()
                else:
                    self.read_cb(line.strip())
        except KeyboardInterrupt:
            sys.stdout.write('\n')

class PromptApplication(ConsoleApplication):
    def create_weboob(self):
        return Weboob(self.APPNAME, scheduler=PromptScheduler(self.prompt, self.read_cb))

    def prompt(self):
        sys.stdout.write('> ')
        sys.stdout.flush()

    def loop(self):
        self.weboob.loop()

    def read_cb(self, line):
        line = line.split()
        self.process_command(*line)

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

import sys
from PyQt4.QtGui import QMainWindow, QApplication

from weboob import Weboob
from weboob.scheduler import Scheduler

from .base import BaseApplication

__all__ = ['QtApplication']

class QtScheduler(Scheduler):
    def __init__(self, app):
        self.app = app

    def run(self):
        self.app.exec_()

class QtApplication(QApplication, BaseApplication):
    def __init__(self):
        QApplication.__init__(self, sys.argv)
        BaseApplication.__init__(self)

    def create_weboob(self):
        return Weboob(self.APPNAME, scheduler=QtScheduler(self))

class QtMainWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

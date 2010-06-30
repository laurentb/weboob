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

from PyQt4.QtGui import QWidget
from PyQt4.QtCore import SIGNAL

from weboob.tools.application.qt import QtMainWindow
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.dating import ICapDating

from weboob.frontends.qboobmsg.messages_manager import MessagesManager

from .ui.main_window_ui import Ui_MainWindow

class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob

        self.ui.tabWidget.addTab(QWidget(), self.tr('Status'))
        self.ui.tabWidget.addTab(MessagesManager(self.weboob), self.tr('Messages'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Contacts'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Calendar'))

        self.connect(self.ui.actionModules, SIGNAL("triggered()"), self.modulesConfig)

    def modulesConfig(self):
        bckndcfg = BackendCfg(self.weboob, (ICapDating,), self)
        bckndcfg.show()

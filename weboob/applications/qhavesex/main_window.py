# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from PyQt4.QtGui import QWidget
from PyQt4.QtCore import SIGNAL

from weboob.tools.application.qt import QtMainWindow
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.dating import ICapDating

try:
    from weboob.applications.qboobmsg.messages_manager import MessagesManager
    HAVE_BOOBMSG = True
except ImportError:
    HAVE_BOOBMSG = False

from .ui.main_window_ui import Ui_MainWindow
from .status import AccountsStatus
from .contacts import ContactsWidget

class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob

        self.loaded_tabs = {}

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)
        self.connect(self.ui.tabWidget, SIGNAL('currentChanged(int)'), self.tabChanged)

        self.ui.tabWidget.addTab(AccountsStatus(self.weboob), self.tr('Status'))
        if HAVE_BOOBMSG:
            self.ui.tabWidget.addTab(MessagesManager(self.weboob), self.tr('Messages'))
        self.ui.tabWidget.addTab(ContactsWidget(self.weboob), self.tr('Contacts'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Calendar'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Optimizations'))

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (ICapDating,), self)
        if bckndcfg.run():
            self.loaded_tabs.clear()
            widget = self.ui.tabWidget.widget(self.ui.tabWidget.currentIndex())
            widget.load()

    def tabChanged(self, i):
        widget = self.ui.tabWidget.currentWidget()

        if hasattr(widget, 'load') and not i in self.loaded_tabs:
            widget.load()
            self.loaded_tabs[i] = True

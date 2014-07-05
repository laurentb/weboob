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

from PyQt4.QtCore import SIGNAL

from weboob.tools.application.qt import QtMainWindow
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.messages import CapMessages

from .ui.main_window_ui import Ui_MainWindow
from .messages_manager import MessagesManager


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.manager = MessagesManager(weboob, self)

        self.setCentralWidget(self.manager)

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)
        self.connect(self.ui.actionRefresh, SIGNAL("triggered()"), self.refresh)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()
        else:
            self.centralWidget().load()

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapMessages,), self)
        if bckndcfg.run():
            self.centralWidget().load()

    def refresh(self):
        self.centralWidget().refreshThreads()

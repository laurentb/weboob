# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtCore import pyqtSlot as Slot

from weboob.tools.application.qt5 import QtMainWindow
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.capabilities.messages import CapMessages

from .ui.main_window_ui import Ui_MainWindow
from .messages_manager import MessagesManager


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.manager = MessagesManager(weboob, self)

        self.setCentralWidget(self.manager)

        self.ui.actionBackends.triggered.connect(self.backendsConfig)
        self.ui.actionRefresh.triggered.connect(self.refresh)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()
        else:
            self.centralWidget().load()

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapMessages,), self)
        if bckndcfg.run():
            self.centralWidget().load()

    @Slot()
    def refresh(self):
        self.centralWidget().refreshThreads()

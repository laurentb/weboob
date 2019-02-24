# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSlot as Slot

from weboob.tools.application.qt5 import QtMainWindow
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.capabilities.dating import CapDating

try:
    from weboob.applications.qboobmsg.messages_manager import MessagesManager
    HAVE_BOOBMSG = True
except ImportError:
    HAVE_BOOBMSG = False

from .ui.main_window_ui import Ui_MainWindow
from .status import AccountsStatus
from .contacts import ContactsWidget
from .events import EventsWidget
from .search import SearchWidget


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob

        self.loaded_tabs = {}

        self.ui.actionBackends.triggered.connect(self.backendsConfig)
        self.ui.tabWidget.currentChanged.connect(self.tabChanged)

        self.addTab(AccountsStatus(self.weboob), self.tr('Status'))
        self.addTab(MessagesManager(self.weboob) if HAVE_BOOBMSG else None, self.tr('Messages'))
        self.addTab(ContactsWidget(self.weboob), self.tr('Contacts'))
        self.addTab(EventsWidget(self.weboob), self.tr('Events'))
        self.addTab(SearchWidget(self.weboob), self.tr('Search'))
        self.addTab(None, self.tr('Calendar'))
        self.addTab(None, self.tr('Optimizations'))

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapDating,), self)
        if bckndcfg.run():
            self.loaded_tabs.clear()
            widget = self.ui.tabWidget.widget(self.ui.tabWidget.currentIndex())
            widget.load()

    def addTab(self, widget, title):
        if widget:
            if getattr(widget, 'display_contact', None):
                widget.display_contact.connect(self.display_contact)
            self.ui.tabWidget.addTab(widget, title)
        else:
            index = self.ui.tabWidget.addTab(QWidget(), title)
            self.ui.tabWidget.setTabEnabled(index, False)

    @Slot(int)
    def tabChanged(self, i):
        widget = self.ui.tabWidget.currentWidget()

        if hasattr(widget, 'load') and i not in self.loaded_tabs:
            widget.load()
            self.loaded_tabs[i] = True

    @Slot(object)
    def display_contact(self, contact):
        self.ui.tabWidget.setCurrentIndex(2)
        widget = self.ui.tabWidget.currentWidget()
        widget.setContact(contact)

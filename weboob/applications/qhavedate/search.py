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

from weboob.tools.application.qt5 import QtDo

from .ui.search_ui import Ui_Search
from .contacts import ContactProfile
from .status import Account


class SearchWidget(QWidget):
    def __init__(self, weboob, parent=None):
        super(SearchWidget, self).__init__(parent)
        self.ui = Ui_Search()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contacts = []
        self.accounts = []
        self.current = None

        self.ui.nextButton.clicked.connect(self.next)
        self.ui.queryButton.clicked.connect(self.sendQuery)

    def load(self):
        while self.ui.statusFrame.layout().count() > 0:
            item = self.ui.statusFrame.layout().takeAt(0)
            if item.widget():
                item.widget().deinit()
                item.widget().hide()
                item.widget().deleteLater()

        self.accounts = []

        for backend in self.weboob.iter_backends():
            account = Account(self.weboob, backend)
            account.title.setText(u'<h2>%s</h2>' % backend.name)
            self.accounts.append(account)
            self.ui.statusFrame.layout().addWidget(account)
        self.ui.statusFrame.layout().addStretch()

        self.getNewProfiles()

    def updateStats(self):
        for account in self.accounts:
            account.updateStats()

    def getNewProfiles(self):
        self.newprofiles_process = QtDo(self.weboob, self.retrieveNewContacts_cb)
        self.newprofiles_process.do('iter_new_contacts')

    def retrieveNewContacts_cb(self, contact):
        self.contacts.insert(0, contact)
        self.ui.queueLabel.setText('%d' % len(self.contacts))
        if self.current is None:
            next(self)

    @Slot()
    def next(self):
        try:
            contact = self.contacts.pop()
        except IndexError:
            contact = None

        self.ui.queueLabel.setText('%d' % len(self.contacts))
        self.setContact(contact)
        self.updateStats()

    def setContact(self, contact):
        self.current = contact
        if contact is not None:
            widget = ContactProfile(self.weboob, contact)
            self.ui.scrollArea.setWidget(widget)
        else:
            self.ui.scrollArea.setWidget(None)

    @Slot()
    def sendQuery(self):
        self.newprofiles_process = QtDo(self.weboob, None, fb=self.next)
        self.newprofiles_process.do('send_query', self.current.id, backends=[self.current.backend])

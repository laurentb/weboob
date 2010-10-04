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

import time

from PyQt4.QtGui import QWidget, QTreeWidgetItem, QListWidgetItem
from PyQt4.QtCore import SIGNAL, Qt

from weboob.capabilities.messages import ICapMessages
from weboob.tools.application.qt import QtDo

from .ui.messages_manager_ui import Ui_MessagesManager

class MessagesManager(QWidget):
    def __init__(self, weboob, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_MessagesManager()
        self.ui.setupUi(self)

        self.weboob = weboob

        self.ui.backendsList.addItem('(All)')
        for backend in self.weboob.iter_backends():
            if not backend.has_caps(ICapMessages):
                continue

            item = QListWidgetItem(backend.name.capitalize())
            item.setData(Qt.UserRole, backend)
            self.ui.backendsList.addItem(item)

        self.ui.backendsList.setCurrentRow(0)
        self.backend = None

        self.connect(self.ui.backendsList, SIGNAL('itemSelectionChanged()'), self._backendChanged)
        self.connect(self.ui.threadsList,  SIGNAL('itemSelectionChanged()'), self._threadChanged)
        self.connect(self.ui.messagesTree, SIGNAL('itemClicked(QTreeWidgetItem *, int)'), self._messageSelected)
        self.connect(self.ui.messagesTree, SIGNAL('itemActivated(QTreeWidgetItem *, int)'), self._messageSelected)

    def load(self):
        self.refreshThreads()

    def _backendChanged(self):
        selection = self.ui.backendsList.selectedItems()
        if not selection:
            self.backend = None
            return

        self.backend = selection[0].data(Qt.UserRole).toPyObject()
        self.refreshThreads()

    def refreshThreads(self):
        self.ui.messagesTree.clear()
        self.ui.threadsList.clear()

        self.process_threads = QtDo(self.weboob, self._gotThread)
        self.process_threads.do('iter_threads', backends=self.backend, caps=ICapMessages)

    def _gotThread(self, backend, thread):
        if not backend:
            self.process_threads = None
            return

        item = QListWidgetItem(thread.title)
        item.setData(Qt.UserRole, (thread.backend, thread.id))
        self.ui.threadsList.addItem(item)

    def _threadChanged(self):
        self.ui.messagesTree.clear()
        selection = self.ui.threadsList.selectedItems()
        if not selection:
            return

        t = selection[0].data(Qt.UserRole).toPyObject()
        print t
        self.refreshThreadMessages(*t)

    def refreshThreadMessages(self, backend, id):
        self.ui.backendsList.setEnabled(False)
        self.ui.threadsList.setEnabled(False)

        self.process = QtDo(self.weboob, self._gotThreadMessages)
        self.process.do('get_thread', id, backends=backend)

    def _gotThreadMessages(self, backend, thread):
        if thread is None:
            self.ui.backendsList.setEnabled(True)
            self.ui.threadsList.setEnabled(True)
            self.process = None
            return

        self._insert_message(thread.root, self.ui.messagesTree.invisibleRootItem())

    def _insert_message(self, message, top):
        item = QTreeWidgetItem(None, [time.strftime('%Y-%m-%d %H:%M:%S', message.date.timetuple()),
                                                      message.sender, message.title])
        item.setData(0, Qt.UserRole, message)

        top.addChild(item)

        for child in message.children:
            self._insert_message(child, item)

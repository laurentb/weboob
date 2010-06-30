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
        self.connect(self.ui.messagesTree, SIGNAL('itemClicked(QTreeWidgetItem *, int)'), self._messageSelected)
        self.connect(self.ui.messagesTree, SIGNAL('itemActivated(QTreeWidgetItem *, int)'), self._messageSelected)
        self.connect(self, SIGNAL('gotMessage'), self._gotMessage)

        self.refresh()

    def _backendChanged(self):
        selection = self.ui.backendsList.selectedItems()
        if not selection:
            self.backend = None
            return

        self.backend = selection[0].data(Qt.UserRole).toPyObject()

        self.ui.messagesTree.clear()
        self.refresh()

    def refresh(self):
        print self.ui.messagesTree.topLevelItemCount()
        if self.ui.messagesTree.topLevelItemCount() > 0:
            command = 'iter_new_messages'
        else:
            command = 'iter_messages'

        self.ui.backendsList.setEnabled(False)

        def cb(backend, message):
            self.emit(SIGNAL('gotMessage'), backend, message)

        def eb(backend, err, backtrace):
            print err
            print backtrace

        if self.backend:
            process = self.weboob.do_backends(self.backend.name, command)
        else:
            process = self.weboob.do_caps(ICapMessages, command)
        self.process = process.callback_thread(cb, eb)

    def _gotMessage(self, backend, message):
        if message is None:
            self.ui.backendsList.setEnabled(True)
            return

        item = QTreeWidgetItem(None, [time.strftime('%Y-%m-%d %H:%M:%S', message.get_date().timetuple()),
                                                      message.sender, message.title])
        item.setData(0, Qt.UserRole, message)

        if not self._insertMessage(self.ui.messagesTree.invisibleRootItem(), item):
            self.ui.messagesTree.addTopLevelItem(item)

    def _insertMessage(self, top, item):
        top_message = top.data(0, Qt.UserRole).toPyObject()
        item_message = item.data(0, Qt.UserRole).toPyObject()

        if top_message and top_message.thread_id == item_message.thread_id and top_message.id == item_message.reply_id:
            top.addChild(item)
            return True
        else:
            for i in xrange(top.childCount()):
                sub = top.child(i)
                if self._insertMessage(sub, item):
                    return True
        return False

    def _messageSelected(self, item, column):
        message = item.data(0, Qt.UserRole).toPyObject()
        self.ui.messageBody.setText("<h1>%s</h1>"
                                    "<b>Date</b>: %s<br />"
                                    "<b>From</b>: %s<br />"
                                    "<p>%s</p>"
                                    % (message.title, str(message.date), message.sender, message.content))

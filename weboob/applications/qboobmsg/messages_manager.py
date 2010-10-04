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
import logging

from PyQt4.QtGui import QWidget, QTreeWidgetItem, QListWidgetItem, QMessageBox
from PyQt4.QtCore import SIGNAL, Qt

from weboob.capabilities.messages import ICapMessages, Message
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
        self.thread = None
        self.message = None

        self.ui.replyButton.setEnabled(False)
        self.ui.replyWidget.hide()

        self.connect(self.ui.backendsList, SIGNAL('itemSelectionChanged()'), self._backendChanged)
        self.connect(self.ui.threadsList,  SIGNAL('itemSelectionChanged()'), self._threadChanged)
        self.connect(self.ui.messagesTree, SIGNAL('itemClicked(QTreeWidgetItem *, int)'), self._messageSelected)
        self.connect(self.ui.messagesTree, SIGNAL('itemActivated(QTreeWidgetItem *, int)'), self._messageSelected)
        self.connect(self.ui.replyButton, SIGNAL('clicked()'), self._replyPressed)
        self.connect(self.ui.sendButton, SIGNAL('clicked()'), self._sendPressed)

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

        self.hideReply()
        self.ui.replyButton.setEnabled(False)
        self.ui.backendsList.setEnabled(False)
        self.ui.threadsList.setEnabled(False)

        self.process_threads = QtDo(self.weboob, self._gotThread)
        self.process_threads.do('iter_threads', backends=self.backend, caps=ICapMessages)

    def _gotThread(self, backend, thread):
        if not backend:
            self.process_threads = None
            self.ui.backendsList.setEnabled(True)
            self.ui.threadsList.setEnabled(True)
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
        self.refreshThreadMessages(*t)

    def refreshThreadMessages(self, backend, id):
        self.ui.messagesTree.clear()
        self.ui.backendsList.setEnabled(False)
        self.ui.threadsList.setEnabled(False)
        self.ui.replyButton.setEnabled(False)
        self.hideReply()

        self.process = QtDo(self.weboob, self._gotThreadMessages)
        self.process.do('get_thread', id, backends=backend)

    def _gotThreadMessages(self, backend, thread):
        if thread is None:
            self.ui.backendsList.setEnabled(True)
            self.ui.threadsList.setEnabled(True)
            self.process = None
            return

        self.thread = thread
        self.showMessage(thread.root)
        self._insert_message(thread.root, self.ui.messagesTree.invisibleRootItem())

    def _insert_message(self, message, top):
        item = QTreeWidgetItem(None, [message.title, message.sender,
                                      time.strftime('%Y-%m-%d %H:%M:%S', message.date.timetuple())])
        item.setData(0, Qt.UserRole, message)

        top.addChild(item)

        for child in message.children:
            self._insert_message(child, item)

    def _messageSelected(self, item, column):
        message = item.data(0, Qt.UserRole).toPyObject()

        self.showMessage(message)

    def showMessage(self, message):
        self.ui.replyButton.setEnabled(True)
        self.message = message

        if message.title.startswith('Re:'):
            self.ui.titleEdit.setText(message.title)
        else:
            self.ui.titleEdit.setText('Re: %s' % message.title)

        if message.flags & message.IS_HTML:
            content = message.content
        else:
            content = message.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        extra = u''
        if message.flags & message.IS_NOT_ACCUSED:
            extra += u'<b>Status</b>: <font color=#ff0000>Unread</font><br />'
        elif message.flags & message.IS_ACCUSED:
            extra += u'<b>Status</b>: <font color=#00ff00>Read</font><br />'
        elif message.flags & message.IS_UNREAD:
            extra += u'<b>Status</b>: <font color=#0000ff>New</font><br />'

        self.ui.messageBody.setText("<h1>%s</h1>"
                                    "<b>Date</b>: %s<br />"
                                    "<b>From</b>: %s<br />"
                                    "%s"
                                    "<p>%s</p>"
                                    % (message.title, str(message.date), message.sender, extra, content))

    def displayReply(self):
        self.ui.replyButton.setText(self.tr('Cancel'))
        self.ui.replyWidget.show()

    def hideReply(self):
        self.ui.replyButton.setText(self.tr('Reply'))
        self.ui.replyWidget.hide()
        self.ui.replyEdit.clear()
        self.ui.titleEdit.clear()

    def _replyPressed(self):
        if self.ui.replyWidget.isVisible():
            self.hideReply()
        else:
            self.displayReply()

    def _sendPressed(self):
        if not self.ui.replyWidget.isVisible():
            return

        text = unicode(self.ui.replyEdit.toPlainText())
        title = unicode(self.ui.titleEdit.text())

        self.ui.backendsList.setEnabled(False)
        self.ui.threadsList.setEnabled(False)
        self.ui.messagesTree.setEnabled(False)
        self.ui.replyButton.setEnabled(False)
        self.ui.replyWidget.setEnabled(False)
        self.ui.sendButton.setText(self.tr('Sending...'))
        flags = 0
        if self.ui.htmlBox.currentIndex() == 0:
            flags = Message.IS_HTML
        m = Message(thread=self.thread,
                    id=0,
                    title=title,
                    sender=None,
                    receiver=None,
                    content=text,
                    parent=self.message,
                    flags=flags)
        self.process_reply = QtDo(self.weboob, self._postReply_cb, self._postReply_eb)
        self.process_reply.do('post_message', m, backends=self.thread.backend)

    def _postReply_cb(self, backend, ignored):
        if not backend:
            return

        self.ui.backendsList.setEnabled(True)
        self.ui.threadsList.setEnabled(True)
        self.ui.messagesTree.setEnabled(True)
        self.ui.replyButton.setEnabled(True)
        self.ui.replyWidget.setEnabled(True)
        self.ui.sendButton.setEnabled(True)
        self.ui.sendButton.setText(self.tr('Send'))
        self.hideReply()
        self.process_reply = None
        self.refreshThreadMessages(backend.name, self.thread.id)

    def _postReply_eb(self, backend, error, backtrace):
        content = unicode(self.tr('Unable to send message:\n%s\n')) % error
        if logging.root.level == logging.DEBUG:
            content += '\n%s\n' % backtrace
        QMessageBox.critical(self, self.tr('Error while posting reply'),
                             content, QMessageBox.Ok)
        self.ui.backendsList.setEnabled(True)
        self.ui.threadsList.setEnabled(True)
        self.ui.messagesTree.setEnabled(True)
        self.ui.replyButton.setEnabled(True)
        self.ui.replyWidget.setEnabled(True)
        self.ui.sendButton.setText(self.tr('Send'))
        self.process_reply = None

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

from __future__ import print_function

import time
import logging

from PyQt4.QtGui import QWidget, QTreeWidgetItem, QListWidgetItem, QMessageBox, QBrush
from PyQt4.QtCore import SIGNAL, Qt

from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message
from weboob.tools.application.qt import QtDo
from weboob.tools.misc import to_unicode

from .ui.messages_manager_ui import Ui_MessagesManager


class MessagesManager(QWidget):
    def __init__(self, weboob, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_MessagesManager()
        self.ui.setupUi(self)

        self.weboob = weboob

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
        self.connect(self.ui.profileButton, SIGNAL('clicked()'), self._profilePressed)
        self.connect(self.ui.replyButton, SIGNAL('clicked()'), self._replyPressed)
        self.connect(self.ui.sendButton, SIGNAL('clicked()'), self._sendPressed)

    def load(self):
        self.ui.backendsList.clear()
        self.ui.backendsList.addItem('(All)')
        for backend in self.weboob.iter_backends():
            if not backend.has_caps(CapMessages):
                continue

            item = QListWidgetItem(backend.name.capitalize())
            item.setData(Qt.UserRole, backend)
            self.ui.backendsList.addItem(item)

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
        self.ui.profileButton.hide()
        self.ui.replyButton.setEnabled(False)
        self.ui.backendsList.setEnabled(False)
        self.ui.threadsList.setEnabled(False)

        self.process_threads = QtDo(self.weboob, self._gotThread, fb=self._gotThreadsEnd)
        self.process_threads.do('iter_threads', backends=self.backend, caps=CapMessages)

    def _gotThreadsEnd(self):
        self.process_threads = None
        self.ui.backendsList.setEnabled(True)
        self.ui.threadsList.setEnabled(True)

    def _gotThread(self, thread):
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
        self.ui.messageBody.clear()
        self.ui.backendsList.setEnabled(False)
        self.ui.threadsList.setEnabled(False)
        self.ui.replyButton.setEnabled(False)
        self.ui.profileButton.hide()
        self.hideReply()

        self.process = QtDo(self.weboob, self._gotThreadMessages, fb=self._gotThreadMessagesEnd)
        self.process.do('get_thread', id, backends=backend)

    def _gotThreadMessagesEnd(self):
        self.ui.backendsList.setEnabled(True)
        self.ui.threadsList.setEnabled(True)
        self.process = None

    def _gotThreadMessages(self, thread):
        self.thread = thread
        if thread.flags & thread.IS_THREADS:
            top = self.ui.messagesTree.invisibleRootItem()
        else:
            top = None

        self._insert_message(thread.root, top)
        self.showMessage(thread.root)

        self.ui.messagesTree.expandAll()

    def _insert_message(self, message, top):
        item = QTreeWidgetItem(None, [message.title or '', message.sender or 'Unknown',
                                      time.strftime('%Y-%m-%d %H:%M:%S', message.date.timetuple())])
        item.setData(0, Qt.UserRole, message)
        if message.flags & message.IS_UNREAD:
            item.setForeground(0, QBrush(Qt.darkYellow))
            item.setForeground(1, QBrush(Qt.darkYellow))
            item.setForeground(2, QBrush(Qt.darkYellow))

        if top is not None:
            # threads
            top.addChild(item)
        else:
            # discussion
            self.ui.messagesTree.invisibleRootItem().insertChild(0, item)

        if message.children is not None:
            for child in message.children:
                self._insert_message(child, top and item)

    def _messageSelected(self, item, column):
        message = item.data(0, Qt.UserRole).toPyObject()

        self.showMessage(message, item)

    def showMessage(self, message, item=None):
        backend = self.weboob.get_backend(message.thread.backend)
        if backend.has_caps(CapMessagesPost):
            self.ui.replyButton.setEnabled(True)
        self.message = message

        if message.title.startswith('Re:'):
            self.ui.titleEdit.setText(message.title)
        else:
            self.ui.titleEdit.setText('Re: %s' % message.title)

        if message.flags & message.IS_HTML:
            content = message.content
        else:
            content = message.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br />')

        extra = u''
        if message.flags & message.IS_NOT_RECEIVED:
            extra += u'<b>Status</b>: <font color=#ff0000>Unread</font><br />'
        elif message.flags & message.IS_RECEIVED:
            extra += u'<b>Status</b>: <font color=#00ff00>Read</font><br />'
        elif message.flags & message.IS_UNREAD:
            extra += u'<b>Status</b>: <font color=#0000ff>New</font><br />'

        self.ui.messageBody.setText("<h1>%s</h1>"
                                    "<b>Date</b>: %s<br />"
                                    "<b>From</b>: %s<br />"
                                    "%s"
                                    "<p>%s</p>"
                                    % (message.title, str(message.date), message.sender, extra, content))

        if item and message.flags & message.IS_UNREAD:
            backend.set_message_read(message)
            message.flags &= ~message.IS_UNREAD
            item.setForeground(0, QBrush())
            item.setForeground(1, QBrush())
            item.setForeground(2, QBrush())

        if message.thread.flags & message.thread.IS_DISCUSSION:
            self.ui.profileButton.show()
        else:
            self.ui.profileButton.hide()

    def _profilePressed(self):
        print(self.thread.id)
        self.emit(SIGNAL('display_contact'), self.thread.id)

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
                    receivers=None,
                    content=text,
                    parent=self.message,
                    flags=flags)
        self.process_reply = QtDo(self.weboob, None, self._postReply_eb, self._postReply_fb)
        self.process_reply.do('post_message', m, backends=self.thread.backend)

    def _postReply_fb(self):
        self.ui.backendsList.setEnabled(True)
        self.ui.threadsList.setEnabled(True)
        self.ui.messagesTree.setEnabled(True)
        self.ui.replyButton.setEnabled(True)
        self.ui.replyWidget.setEnabled(True)
        self.ui.sendButton.setEnabled(True)
        self.ui.sendButton.setText(self.tr('Send'))
        self.hideReply()
        self.process_reply = None
        self.refreshThreadMessages(self.thread.backend, self.thread.id)

    def _postReply_eb(self, backend, error, backtrace):
        content = unicode(self.tr('Unable to send message:\n%s\n')) % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while posting reply'),
                             content, QMessageBox.Ok)
        self.ui.backendsList.setEnabled(True)
        self.ui.threadsList.setEnabled(True)
        self.ui.messagesTree.setEnabled(True)
        self.ui.replyButton.setEnabled(True)
        self.ui.replyWidget.setEnabled(True)
        self.ui.sendButton.setText(self.tr('Send'))
        self.process_reply = None

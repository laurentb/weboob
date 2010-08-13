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
from PyQt4.QtGui import QWidget, QListWidgetItem, QImage, QIcon, QPixmap, \
                        QFrame, QMessageBox, QTabWidget, QVBoxLayout, \
                        QFormLayout, QLabel
from PyQt4.QtCore import SIGNAL, Qt

from weboob.tools.application.qt import QtDo, HTMLDelegate
from weboob.capabilities.contact import ICapContact, Contact
from weboob.capabilities.chat import ICapChat
from weboob.capabilities.messages import ICapMessages

from .ui.contacts_ui import Ui_Contacts
from .ui.contact_thread_ui import Ui_ContactThread
from .ui.thread_message_ui import Ui_ThreadMessage
from .ui.profile_ui import Ui_Profile

class ThreadMessage(QFrame):
    """
    This class represents a message in the thread tab.
    """

    def __init__(self, message, parent=None):
        QFrame.__init__(self, parent)
        self.ui = Ui_ThreadMessage()
        self.ui.setupUi(self)

        self.date = message.date

        self.ui.nameLabel.setText(message.sender)
        self.ui.headerLabel.setText(time.strftime('%Y-%m-%d %H:%M:%S', message.date.timetuple()))
        if message.flags & message.IS_HTML:
            content = message.content
        else:
            content = message.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br />')
        self.ui.contentLabel.setText(content)

class ContactThread(QWidget):
    """
    The thread of the selected contact.
    """

    def __init__(self, weboob, contact, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_ContactThread()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = contact
        self.messages = []

        self.connect(self.ui.sendButton, SIGNAL('clicked()'), self.postReply)

        self.refreshMessages()

    def refreshMessages(self):
        if self.ui.scrollAreaContent.layout().count() > 0:
            command = 'iter_new_messages'
        else:
            command = 'iter_messages'

        self.process_msg = QtDo(self.weboob, self.gotMessage)
        self.process_msg.do(command, thread=self.contact.id, backends=self.contact.backend)

    def gotMessage(self, backend, message):
        if not message:
            #v = self.ui.scrollArea.verticalScrollBar()
            #print v.minimum(), v.value(), v.maximum(), v.sliderPosition()
            #self.ui.scrollArea.verticalScrollBar().setValue(self.ui.scrollArea.verticalScrollBar().maximum())
            self.process_msg = None
            return

        widget = ThreadMessage(message)
        for i, m in enumerate(self.messages):
            if widget.date > m.date:
                self.ui.scrollAreaContent.layout().insertWidget(i, widget)
                self.messages.insert(i, widget)
                return

        self.ui.scrollAreaContent.layout().addWidget(widget)
        self.messages.append(widget)

    def postReply(self):
        text = unicode(self.ui.textEdit.toPlainText())
        self.ui.textEdit.setEnabled(False)
        self.ui.sendButton.setEnabled(False)
        self.process_reply = QtDo(self.weboob, self._postReply_cb, self._postReply_eb)
        self.process_reply.do('post_reply', self.contact.id, 0, '', text, backends=self.contact.backend)

    def _postReply_cb(self, backend, ignored):
        self.ui.textEdit.clear()
        self.ui.textEdit.setEnabled(True)
        self.ui.sendButton.setEnabled(True)
        self.refreshMessages()
        self.process_reply = None

    def _postReply_eb(self, backend, error, backtrace):
        content = unicode(self.tr('Unable to send message:\n%s\n')) % error
        if logging.root.level == logging.DEBUG:
            content += '\n%s\n' % backtrace
        QMessageBox.critical(self, self.tr('Error while posting reply'),
                             content, QMessageBox.Ok)
        self.process_reply = None

class ContactProfile(QWidget):
    def __init__(self, weboob, contact, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_Profile()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = contact

        if self.gotProfile(self.weboob.get_backend(contact.backend), contact):
            self.process_contact = QtDo(self.weboob, self.gotProfile)
            self.process_contact.do('fillobj', self.contact, ['photos', 'profile'], backends=self.contact.backend)

    def gotProfile(self, backend, contact):
        if not backend:
            return

        first = True
        for photo in contact.photos.itervalues():
            photo = contact.photos.values()[0]
            if first and photo.data:
                img = QImage.fromData(photo.data)
                self.ui.photoLabel.setPixmap(QPixmap.fromImage(img))
                first = False
            else:
                # TODO display thumbnails
                pass

        self.ui.nicknameLabel.setText('<h1>%s</h1>' % contact.name)
        self.ui.statusLabel.setText('%s' % contact.status_msg)
        self.ui.descriptionEdit.setText('<h1>Description</h1><p>%s</p>' % (contact.summary.replace('\n', '<br />') or '<i>Receiving...</i>'))

        if not contact.profile:
            return True

        for head in contact.profile:
            if head.flags & head.HEAD:
                widget = self.ui.headFrame
            else:
                widget = self.ui.profileTab
            self.process_node(head, widget)

        return False

    def process_node(self, node, widget):
        # Set the value widget
        value = None
        if node.flags & node.SECTION:
            value = QWidget()
            value.setLayout(QFormLayout())
            for sub in node.value:
                self.process_node(sub, value)
        elif isinstance(node.value, list):
            value = QLabel('<br />'.join([unicode(s) for s in node.value]))
            value.setWordWrap(True)
        elif isinstance(node.value, tuple):
            value = QLabel(', '.join([unicode(s) for s in node.value]))
            value.setWordWrap(True)
        elif isinstance(node.value, (str,unicode,int,long,float)):
            value = QLabel(unicode(node.value))
        else:
            logging.warning('Not supported value: %r' % node.value)
            return

        # Insert the value widget into the parent widget, depending
        # of its type.
        if isinstance(widget, QTabWidget):
            widget.addTab(value, node.label)
        elif isinstance(widget.layout(), QFormLayout):
            label = QLabel(u'<b>%s:</b> ' % node.label)
            widget.layout().addRow(label, value)
        elif isinstance(widget.layout(), QVBoxLayout):
            widget.layout().addWidget(value)
        else:
            logging.warning('Not supported widget: %r' % widget)

class IGroup(object):
    def __init__(self, weboob, id, name):
        self.id = id
        self.name = name
        self.weboob = weboob

    def iter_contacts(self, cb):
        raise NotImplementedError()

class MetaGroup(IGroup):
    def iter_contacts(self, cb):
        if self.id == 'online':
            status = Contact.STATUS_ONLINE|Contact.STATUS_AWAY
        elif self.id == 'offline':
            status = Contact.STATUS_OFFLINE
        else:
            status = Contact.STATUS_ALL

        self.process = QtDo(self.weboob, lambda b, d: self.cb(cb, b, d))
        self.process.do('iter_contacts', status, caps=ICapContact)

    def cb(self, cb, backend, contact):
        if contact:
            cb(contact)
        elif not backend:
            self.process = None
            cb(None)

class ContactsWidget(QWidget):
    def __init__(self, weboob, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_Contacts()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = None
        self.ui.contactList.setItemDelegate(HTMLDelegate())

        self.ui.groupBox.addItem('All', MetaGroup(self.weboob, 'all', self.tr('All')))
        self.ui.groupBox.addItem('Onlines', MetaGroup(self.weboob, 'online', self.tr('Online')))
        self.ui.groupBox.addItem('Offlines', MetaGroup(self.weboob, 'offline', self.tr('Offline')))
        self.ui.groupBox.setCurrentIndex(1)

        self.connect(self.ui.groupBox, SIGNAL('currentIndexChanged(int)'), self.groupChanged)
        self.connect(self.ui.contactList, SIGNAL('currentItemChanged(QListWidgetItem*, QListWidgetItem*)'), self.contactChanged)
        self.connect(self.ui.refreshButton, SIGNAL('clicked()'), self.refreshContactList)

    def load(self):
        self.refreshContactList()

    def groupChanged(self, i):
        self.refreshContactList()

    def refreshContactList(self):
        self.ui.contactList.clear()
        i = self.ui.groupBox.currentIndex()
        group = self.ui.groupBox.itemData(i).toPyObject()
        group.iter_contacts(self.addContact)

    def setPhoto(self, contact, item):
        if not contact:
            return

        img = None
        for photo in contact.photos.itervalues():
            if photo.thumbnail_data:
                img = QImage.fromData(photo.thumbnail_data)
                break

        if img:
            item.setIcon(QIcon(QPixmap.fromImage(img)))

    def addContact(self, contact):
        if not contact:
            return

        status = ''
        if contact.status == Contact.STATUS_ONLINE:
            status = u'Online'
            status_color = 0x00aa00
        elif contact.status == Contact.STATUS_OFFLINE:
            status = u'Offline'
            status_color = 0xff0000
        elif contact.status == Contact.STATUS_AWAY:
            status = u'Away'
            status_color = 0xffad16
        else:
            status = u'Unknown'
            status_color = 0xaaaaaa

        if contact.status_msg:
            status += u' — %s' % contact.status_msg

        item = QListWidgetItem()
        item.setText('<h2>%s</h2><font color="#%06X">%s</font><br /><i>%s</i>' % (contact.name, status_color, status, contact.backend))
        item.setData(Qt.UserRole, contact)

        process = QtDo(self.weboob, lambda b, c: self.setPhoto(c, item))
        process.do('fillobj', contact, ['photos'], backends=contact.backend)

        for i in xrange(self.ui.contactList.count()):
            if self.ui.contactList.item(i).data(Qt.UserRole).toPyObject().status > contact.status:
                self.ui.contactList.insertItem(i, item)
                return

        self.ui.contactList.addItem(item)

    def contactChanged(self, current, previous):
        self.ui.tabWidget.clear()
        self.contact = None

        if not current:
            return

        self.contact = current.data(Qt.UserRole).toPyObject()

        if not self.contact:
            return

        backend = self.weboob.get_backend(self.contact.backend)

        self.ui.tabWidget.addTab(ContactProfile(self.weboob, self.contact), self.tr('Profile'))
        if backend.has_caps(ICapMessages):
            self.ui.tabWidget.addTab(ContactThread(self.weboob, self.contact), self.tr('Messages'))
        if backend.has_caps(ICapChat):
            self.ui.tabWidget.addTab(QWidget(), self.tr('Chat'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Calendar'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Notes'))

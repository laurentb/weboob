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

import time
import logging
from PyQt5.QtGui import QImage, QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QListWidgetItem, QFrame, \
                            QMessageBox, QTabWidget, QVBoxLayout, \
                            QFormLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.tools.application.qt5 import QtDo, HTMLDelegate
from weboob.tools.application.qt5.models import BackendListModel
from weboob.tools.compat import range, basestring, unicode, long
from weboob.tools.misc import to_unicode
from weboob.capabilities.contact import CapContact, Contact
from weboob.capabilities.chat import CapChat
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message
from weboob.capabilities.base import NotLoaded

from .ui.contacts_ui import Ui_Contacts
from .ui.contact_thread_ui import Ui_ContactThread
from .ui.thread_message_ui import Ui_ThreadMessage
from .ui.profile_ui import Ui_Profile
from .ui.notes_ui import Ui_Notes


class ThreadMessage(QFrame):
    """
    This class represents a message in the thread tab.
    """

    def __init__(self, message, parent=None):
        super(ThreadMessage, self).__init__(parent)
        self.ui = Ui_ThreadMessage()
        self.ui.setupUi(self)

        self.set_message(message)

    def set_message(self, message):
        self.message = message

        self.ui.nameLabel.setText(message.sender)
        header = time.strftime('%Y-%m-%d %H:%M:%S', message.date.timetuple())
        if message.flags & message.IS_NOT_RECEIVED:
            header += u' — <font color=#ff0000>Unread</font>'
        elif message.flags & message.IS_RECEIVED:
            header += u' — <font color=#00ff00>Read</font>'
        self.ui.headerLabel.setText(header)
        if message.flags & message.IS_HTML:
            content = message.content
        else:
            content = message.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br />')
        self.ui.contentLabel.setText(content)

    def __eq__(self, m):
        if not isinstance(m, Message):
            return False
        return self.message == m.message


class ContactThread(QWidget):
    """
    The thread of the selected contact.
    """

    def __init__(self, weboob, contact, support_reply, parent=None):
        super(ContactThread, self).__init__(parent)
        self.ui = Ui_ContactThread()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = contact
        self.thread = None
        self.messages = []
        self.process_msg = None
        self.ui.refreshButton.clicked.connect(self.refreshMessages)

        if support_reply:
            self.ui.sendButton.clicked.connect(self.postReply)
        else:
            self.ui.frame.hide()

        self.refreshMessages()

    @Slot()
    def refreshMessages(self, fillobj=False):
        if self.process_msg:
            return

        self.ui.refreshButton.setEnabled(False)

        def finished():
            #v = self.ui.scrollArea.verticalScrollBar()
            #print v.minimum(), v.value(), v.maximum(), v.sliderPosition()
            #self.ui.scrollArea.verticalScrollBar().setValue(self.ui.scrollArea.verticalScrollBar().maximum())
            self.process_msg = None

        self.process_msg = QtDo(self.weboob, self.gotThread, self.gotError, finished)
        if fillobj and self.thread:
            self.process_msg.do('fillobj', self.thread, ['root'], backends=self.contact.backend)
        else:
            self.process_msg.do('get_thread', self.contact.id, backends=self.contact.backend)

    def gotError(self, backend, error, backtrace):
        self.ui.textEdit.setEnabled(False)
        self.ui.sendButton.setEnabled(False)
        self.ui.refreshButton.setEnabled(True)

    def gotThread(self, thread):
        self.ui.textEdit.setEnabled(True)
        self.ui.sendButton.setEnabled(True)
        self.ui.refreshButton.setEnabled(True)

        self.thread = thread

        if thread.root is NotLoaded:
            self._insert_load_button(0)
        else:
            for message in thread.iter_all_messages():
                self._insert_message(message)

    def _insert_message(self, message):
        widget = ThreadMessage(message)
        if widget in self.messages:
            old_widget = self.messages[self.messages.index(widget)]
            if old_widget.message.flags != widget.message.flags:
                old_widget.set_message(widget.message)
            return

        for i, m in enumerate(self.messages):
            if widget.message.date > m.message.date:
                self.ui.scrollAreaContent.layout().insertWidget(i, widget)
                self.messages.insert(i, widget)
                if message.parent is NotLoaded:
                    self._insert_load_button(i)
                return

        self.ui.scrollAreaContent.layout().addWidget(widget)
        self.messages.append(widget)
        if message.parent is NotLoaded:
            self._insert_load_button(-1)

    def _insert_load_button(self, pos):
        button = QPushButton(self.tr('More messages...'))
        button.clicked.connect(self._load_button_pressed)
        if pos >= 0:
            self.ui.scrollAreaContent.layout().insertWidget(pos, button)
        else:
            self.ui.scrollAreaContent.layout().addWidget(button)

    @Slot()
    def _load_button_pressed(self):
        button = self.sender()
        self.ui.scrollAreaContent.layout().removeWidget(button)
        button.hide()
        button.deleteLater()

        self.refreshMessages(fillobj=True)

    @Slot()
    def postReply(self):
        text = self.ui.textEdit.toPlainText()
        self.ui.textEdit.setEnabled(False)
        self.ui.sendButton.setEnabled(False)
        m = Message(thread=self.thread,
                    id=0,
                    title=u'',
                    sender=None,
                    receivers=None,
                    content=text,
                    parent=self.messages[0].message if len(self.messages) > 0 else None)
        self.process_reply = QtDo(self.weboob, None, self._postReply_eb, self._postReply_fb)
        self.process_reply.do('post_message', m, backends=self.contact.backend)

    def _postReply_fb(self):
        self.ui.textEdit.clear()
        self.ui.textEdit.setEnabled(True)
        self.ui.sendButton.setEnabled(True)
        self.refreshMessages()
        self.process_reply = None

    def _postReply_eb(self, backend, error, backtrace):
        content = self.tr('Unable to send message:\n%s\n') % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while posting reply'),
                             content, QMessageBox.Ok)
        self.process_reply = None


class ContactProfile(QWidget):
    def __init__(self, weboob, contact, parent=None):
        super(ContactProfile, self).__init__(parent)
        self.ui = Ui_Profile()
        self.ui.setupUi(self)

        self.ui.previousButton.clicked.connect(self.previousClicked)
        self.ui.nextButton.clicked.connect(self.nextClicked)

        self.weboob = weboob
        self.contact = contact
        self.loaded_profile = False
        self.displayed_photo_idx = 0
        self.process_photo = {}

        missing_fields = self.gotProfile(contact)
        if len(missing_fields) > 0:
            self.process_contact = QtDo(self.weboob, self.gotProfile, self.gotError)
            self.process_contact.do('fillobj', self.contact, missing_fields, backends=self.contact.backend)

    def gotError(self, backend, error, backtrace):
        self.ui.frame_photo.hide()
        self.ui.descriptionEdit.setText('<h1>Unable to show profile</h1><p>%s</p>' % to_unicode(error))

    def gotProfile(self, contact):
        missing_fields = set()

        self.display_photo()

        self.ui.nicknameLabel.setText('<h1>%s</h1>' % contact.name)
        if contact.status == Contact.STATUS_ONLINE:
            status_color = 0x00aa00
        elif contact.status == Contact.STATUS_OFFLINE:
            status_color = 0xff0000
        elif contact.status == Contact.STATUS_AWAY:
            status_color = 0xffad16
        else:
            status_color = 0xaaaaaa

        self.ui.statusLabel.setText('<font color="#%06X">%s</font>' % (status_color, contact.status_msg))
        self.ui.contactUrlLabel.setText('<b>URL:</b> <a href="%s">%s</a>' % (contact.url, contact.url))
        if contact.summary is NotLoaded:
            self.ui.descriptionEdit.setText('<h1>Description</h1><p><i>Receiving...</i></p>')
            missing_fields.add('summary')
        elif contact.summary:
            self.ui.descriptionEdit.setText('<h1>Description</h1><p>%s</p>' % contact.summary.replace('\n', '<br />'))

        if not contact.profile:
            missing_fields.add('profile')
        elif not self.loaded_profile:
            self.loaded_profile = True
            for head in contact.profile.values():
                if head.flags & head.HEAD:
                    widget = self.ui.headWidget
                else:
                    widget = self.ui.profileTab
                self.process_node(head, widget)

        return missing_fields

    def process_node(self, node, widget):
        # Set the value widget
        value = None
        if node.flags & node.SECTION:
            value = QWidget()
            value.setLayout(QFormLayout())
            for sub in node.value.values():
                self.process_node(sub, value)
        elif isinstance(node.value, list):
            value = QLabel('<br />'.join(unicode(s) for s in node.value))
            value.setWordWrap(True)
        elif isinstance(node.value, tuple):
            value = QLabel(', '.join(unicode(s) for s in node.value))
            value.setWordWrap(True)
        elif isinstance(node.value, (basestring,int,long,float)):
            value = QLabel(unicode(node.value))
        else:
            logging.warning('Not supported value: %r' % node.value)
            return

        if isinstance(value, QLabel):
            value.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard|Qt.LinksAccessibleByMouse)

        # Insert the value widget into the parent widget, depending
        # of its type.
        if isinstance(widget, QTabWidget):
            widget.addTab(value, node.label)
        elif isinstance(widget.layout(), QFormLayout):
            label = QLabel(u'<b>%s:</b> ' % node.label)
            widget.layout().addRow(label, value)
        elif isinstance(widget.layout(), QVBoxLayout):
            widget.layout().addWidget(QLabel(u'<h3>%s</h3>' % node.label))
            widget.layout().addWidget(value)
        else:
            logging.warning('Not supported widget: %r' % widget)

    @Slot()
    def previousClicked(self):
        if len(self.contact.photos) == 0:
            return
        self.displayed_photo_idx = (self.displayed_photo_idx - 1) % len(self.contact.photos)
        self.display_photo()

    @Slot()
    def nextClicked(self):
        if len(self.contact.photos) == 0:
            return
        self.displayed_photo_idx = (self.displayed_photo_idx + 1) % len(self.contact.photos)
        self.display_photo()

    def display_photo(self):
        if self.displayed_photo_idx >= len(self.contact.photos) or self.displayed_photo_idx < 0:
            self.displayed_photo_idx = len(self.contact.photos) - 1
        if self.displayed_photo_idx < 0:
            self.ui.photoUrlLabel.setText('')
            return

        photo = list(self.contact.photos.values())[self.displayed_photo_idx]
        if photo.data:
            data = photo.data
            if photo.id in self.process_photo:
                self.process_photo.pop(photo.id)
        else:
            self.process_photo[photo.id] = QtDo(self.weboob, lambda p: self.display_photo())
            self.process_photo[photo.id].do('fillobj', photo, ['data'], backends=self.contact.backend)

            if photo.thumbnail_data:
                data = photo.thumbnail_data
            else:
                return

        img = QImage.fromData(data)
        img = img.scaledToWidth(self.width()/3)

        self.ui.photoLabel.setPixmap(QPixmap.fromImage(img))
        if photo.url is not NotLoaded:
            text = '<a href="%s">%s</a>' % (photo.url, photo.url)
            if photo.hidden:
                text += '<br /><font color=#ff0000><i>(Hidden photo)</i></font>'
            self.ui.photoUrlLabel.setText(text)


class ContactNotes(QWidget):
    """ Widget for storing notes about a contact """

    def __init__(self, weboob, contact, parent=None):
        super(ContactNotes, self).__init__(parent)
        self.ui = Ui_Notes()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = contact

        self.ui.textEdit.setEnabled(False)
        self.ui.saveButton.setEnabled(False)

        def finished():
            self.process = None
            self.ui.textEdit.setEnabled(True)
            self.ui.saveButton.setEnabled(True)

        self.process = QtDo(self.weboob, self._getNotes_cb, self._getNotes_eb, finished)
        self.process.do('get_notes', self.contact.id, backends=(self.contact.backend,))

        self.ui.saveButton.clicked.connect(self.saveNotes)

    def _getNotes_cb(self, data):
        if data:
            self.ui.textEdit.setText(data)

    def _getNotes_eb(self, backend, error, backtrace):
        if isinstance(error, NotImplementedError):
            return

        self.ui.textEdit.setEnabled(True)
        self.ui.saveButton.setEnabled(True)
        content = self.tr('Unable to load notes:\n%s\n') % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
            QMessageBox.critical(self, self.tr('Error while loading notes'),
            content, QMessageBox.Ok)

    @Slot()
    def saveNotes(self):
        text = self.ui.textEdit.toPlainText()
        self.ui.saveButton.setEnabled(False)
        self.ui.textEdit.setEnabled(False)

        self.process = QtDo(self.weboob, None, self._saveNotes_eb, self._saveNotes_fb)
        self.process.do('save_notes', self.contact.id, text, backends=(self.contact.backend,))

    def _saveNotes_fb(self):
        self.ui.saveButton.setEnabled(True)
        self.ui.textEdit.setEnabled(True)

    def _saveNotes_eb(self, backend, error, backtrace):
        content = self.tr('Unable to save notes:\n%s\n') % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
            QMessageBox.critical(self, self.tr('Error while saving notes'),
            content, QMessageBox.Ok)


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

        self.process = QtDo(self.weboob, lambda d: self.cb(cb, d), fb=lambda: self.fb(cb))
        self.process.do('iter_contacts', status, caps=CapContact)

    def cb(self, cb, contact):
        if contact:
            cb(contact)

    def fb(self, fb):
        self.process = None
        if fb:
            fb(None)


class ContactsWidget(QWidget):
    def __init__(self, weboob, parent=None):
        super(ContactsWidget, self).__init__(parent)
        self.ui = Ui_Contacts()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = None
        self.ui.contactList.setItemDelegate(HTMLDelegate())

        self.url_process = None
        self.photo_processes = {}

        self.ui.groupBox.addItem('All', MetaGroup(self.weboob, 'all', self.tr('All')))
        self.ui.groupBox.addItem('Online', MetaGroup(self.weboob, 'online', self.tr('Online')))
        self.ui.groupBox.addItem('Offline', MetaGroup(self.weboob, 'offline', self.tr('Offline')))
        self.ui.groupBox.setCurrentIndex(1)

        self.ui.groupBox.currentIndexChanged.connect(self.groupChanged)
        self.ui.contactList.itemClicked.connect(self.contactChanged)
        self.ui.refreshButton.clicked.connect(self.refreshContactList)
        self.ui.urlButton.clicked.connect(self.urlClicked)

    def load(self):
        self.refreshContactList()
        model = BackendListModel(self.weboob)
        model.addBackends(entry_all=False)
        self.ui.backendsList.setModel(model)

    @Slot()
    def groupChanged(self):
        self.refreshContactList()

    @Slot()
    def refreshContactList(self):
        self.ui.contactList.clear()
        self.ui.refreshButton.setEnabled(False)
        i = self.ui.groupBox.currentIndex()
        group = self.ui.groupBox.itemData(i)
        group.iter_contacts(self.addContact)

    def setPhoto(self, contact, item):
        if not contact:
            return False

        try:
            self.photo_processes.pop(contact.id, None)
        except KeyError:
            pass

        img = None
        for photo in contact.photos.values():
            if photo.thumbnail_data:
                img = QImage.fromData(photo.thumbnail_data)
                break

        if img:
            item.setIcon(QIcon(QPixmap.fromImage(img)))
            return True

        return False

    def addContact(self, contact):
        if not contact:
            self.ui.refreshButton.setEnabled(True)
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

        if contact.photos is NotLoaded:
            process = QtDo(self.weboob, lambda c: self.setPhoto(c, item))
            process.do('fillobj', contact, ['photos'], backends=contact.backend)
            self.photo_processes[contact.id] = process
        elif len(contact.photos) > 0:
            if not self.setPhoto(contact, item):
                photo = list(contact.photos.values())[0]
                process = QtDo(self.weboob, lambda p: self.setPhoto(contact, item))
                process.do('fillobj', photo, ['thumbnail_data'], backends=contact.backend)
                self.photo_processes[contact.id] = process

        for i in range(self.ui.contactList.count()):
            if self.ui.contactList.item(i).data(Qt.UserRole).status > contact.status:
                self.ui.contactList.insertItem(i, item)
                return

        self.ui.contactList.addItem(item)

    @Slot(QListWidgetItem)
    def contactChanged(self, current):
        if not current:
            return

        contact = current.data(Qt.UserRole)
        self.setContact(contact)

    def setContact(self, contact):
        if not contact or contact == self.contact:
            return

        if not isinstance(contact, Contact):
            return self.retrieveContact(contact)

        self.ui.tabWidget.clear()
        self.contact = contact
        backend = self.weboob.get_backend(self.contact.backend)

        self.ui.tabWidget.addTab(ContactProfile(self.weboob, self.contact), self.tr('Profile'))
        if backend.has_caps(CapMessages):
            self.ui.tabWidget.addTab(ContactThread(self.weboob, self.contact, backend.has_caps(CapMessagesPost)), self.tr('Messages'))
        if backend.has_caps(CapChat):
            self.ui.tabWidget.setTabEnabled(self.ui.tabWidget.addTab(QWidget(), self.tr('Chat')),
                                            False)
        self.ui.tabWidget.setTabEnabled(self.ui.tabWidget.addTab(QWidget(), self.tr('Calendar')),
                                        False)
        self.ui.tabWidget.addTab(ContactNotes(self.weboob, self.contact), self.tr('Notes'))

    @Slot()
    def urlClicked(self):
        url = self.ui.urlEdit.text()
        if not url:
            return

        self.retrieveContact(url)

    def retrieveContact(self, url):
        backend_name = self.ui.backendsList.currentText()
        self.ui.urlButton.setEnabled(False)

        def finished():
            self.url_process = None
            self.ui.urlButton.setEnabled(True)

        self.url_process = QtDo(self.weboob, self.retrieveContact_cb, self.retrieveContact_eb, finished)
        self.url_process.do('get_contact', url, backends=backend_name)

    def retrieveContact_cb(self, contact):
        self.ui.urlEdit.clear()
        self.setContact(contact)

    def retrieveContact_eb(self, backend, error, backtrace):
        content = self.tr('Unable to get contact:\n%s\n') % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += u'\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while getting contact'),
                             content, QMessageBox.Ok)

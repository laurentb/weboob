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

import urllib2
from PyQt4.QtGui import QWidget, QListWidgetItem, QImage, QIcon, QPixmap
from PyQt4.QtCore import SIGNAL, Qt

from weboob.tools.application.qt import QtDo
from weboob.capabilities.contact import ICapContact, Contact
from weboob.capabilities.chat import ICapChat
from weboob.capabilities.messages import ICapMessages

from .ui.contacts_ui import Ui_Contacts

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
            status = Contact.STATUS_ONLINE
        elif self.id == 'offline':
            status = Contact.STATUS_OFFLINE
        else:
            status = Contact.STATUS_ALL

        self.process = QtDo(self.weboob, lambda b, d: self.cb(cb, b, d))
        self.process.do_caps(ICapContact, 'iter_contacts', status)

    def cb(self, cb, backend, contact):
        if contact:
            contact.backend = backend
        cb(contact)

class ContactsWidget(QWidget):
    def __init__(self, weboob, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_Contacts()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.contact = None

        self.ui.groupBox.addItem('All', MetaGroup(self.weboob, 'all', self.tr('All')))
        self.ui.groupBox.addItem('Onlines', MetaGroup(self.weboob, 'online', self.tr('Online')))
        self.ui.groupBox.addItem('Offlines', MetaGroup(self.weboob, 'offline', self.tr('Offline')))

        self.connect(self.ui.groupBox, SIGNAL('currentIndexChanged(int)'), self.groupChanged)
        self.connect(self.ui.contactList, SIGNAL('currentItemChanged(QListWidgetItem*, QListWidgetItem*)'), self.contactChanged)

    def load(self):
        self.ui.groupBox.setCurrentIndex(1)

    def groupChanged(self, i):
        self.ui.contactList.clear()
        group = self.ui.groupBox.itemData(i).toPyObject()
        group.iter_contacts(self.addContact)

    def addContact(self, contact):
        if not contact:
            return

        data = urllib2.urlopen(contact.thumbnail_url).read()
        img = QImage.fromData(data)

        status = ''
        if contact.status == Contact.STATUS_ONLINE:
            status = 'Online'
        elif contact.status == Contact.STATUS_OFFLINE:
            status = 'Offline'

        item = QListWidgetItem()
        item.setText('%s\n> %s\n(%s)' % (contact.name, status, contact.backend.name))
        item.setIcon(QIcon(QPixmap.fromImage(img)))
        item.setData(Qt.UserRole, contact)

        self.ui.contactList.addItem(item)

    def contactChanged(self, current, previous):
        contact = current.data(Qt.UserRole).toPyObject()

        self.ui.tabWidget.clear()

        self.ui.tabWidget.addTab(QWidget(), self.tr('Profile'))
        if contact.backend.has_caps(ICapMessages):
            self.ui.tabWidget.addTab(QWidget(), self.tr('Messages'))
        if contact.backend.has_caps(ICapChat):
            self.ui.tabWidget.addTab(QWidget(), self.tr('Chat'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Calendar'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Notes'))
        print contact.backend

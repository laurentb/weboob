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

from __future__ import print_function

from PyQt5.QtGui import QImage, QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot

from weboob.capabilities.base import NotLoaded
from weboob.tools.compat import range
from weboob.tools.application.qt5 import QtDo, HTMLDelegate

from .ui.events_ui import Ui_Events


class EventsWidget(QWidget):
    display_contact = Signal(object)

    def __init__(self, weboob, parent=None):
        super(EventsWidget, self).__init__(parent)
        self.ui = Ui_Events()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.photo_processes = {}
        self.event_filter = None

        self.ui.eventsList.itemDoubleClicked.connect(self.eventDoubleClicked)
        self.ui.typeBox.currentIndexChanged.connect(self.typeChanged)
        self.ui.refreshButton.clicked.connect(self.refreshEventsList)

        self.ui.eventsList.setItemDelegate(HTMLDelegate())
        self.ui.eventsList.sortByColumn(1, Qt.DescendingOrder)

    def load(self):
        self.refreshEventsList()

    @Slot(int)
    def typeChanged(self, i):
        if self.ui.refreshButton.isEnabled():
            self.refreshEventsList()

    @Slot()
    def refreshEventsList(self):
        self.ui.eventsList.clear()
        self.ui.refreshButton.setEnabled(False)
        if self.ui.typeBox.currentIndex() >= 0:
            # XXX strangely, in gotEvent() in the loop to check if there is already the
            # event type to try to introduce it in list, itemData() returns the right value.
            # But, I don't know why, here, it will ALWAYS return None...
            # So the filter does not work currently.
            self.events_filter = self.ui.typeBox.itemData(self.ui.typeBox.currentIndex())
        else:
            self.event_filter = None
        self.ui.typeBox.setEnabled(False)
        self.ui.typeBox.clear()
        self.ui.typeBox.addItem('All', None)

        def finished():
            self.ui.refreshButton.setEnabled(True)
            self.ui.typeBox.setEnabled(True)

        self.process = QtDo(self.weboob, self.gotEvent, fb=finished)
        self.process.do('iter_events')

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
            item.setIcon(0, QIcon(QPixmap.fromImage(img)))
            self.ui.eventsList.resizeColumnToContents(0)
            return True

        return False

    def gotEvent(self, event):
        found = False
        for i in range(self.ui.typeBox.count()):
            s = self.ui.typeBox.itemData(i)
            if s == event.type:
                found = True
        if not found:
            print(event.type)
            self.ui.typeBox.addItem(event.type.capitalize(), event.type)
            if event.type == self.event_filter:
                self.ui.typeBox.setCurrentIndex(self.ui.typeBox.count()-1)

        if self.event_filter and self.event_filter != event.type:
            return

        if not event.contact:
            return

        contact = event.contact
        contact.backend = event.backend
        status = ''

        if contact.status == contact.STATUS_ONLINE:
            status = u'Online'
            status_color = 0x00aa00
        elif contact.status == contact.STATUS_OFFLINE:
            status = u'Offline'
            status_color = 0xff0000
        elif contact.status == contact.STATUS_AWAY:
            status = u'Away'
            status_color = 0xffad16
        else:
            status = u'Unknown'
            status_color = 0xaaaaaa

        if contact.status_msg:
            status += u' — %s' % contact.status_msg

        name = '<h2>%s</h2><font color="#%06X">%s</font><br /><i>%s</i>' % (contact.name, status_color, status, event.backend)
        date = event.date.strftime('%Y-%m-%d %H:%M')
        type = event.type
        message = event.message

        item = QTreeWidgetItem(None, [name, date, type, message])
        item.setData(0, Qt.UserRole, event)
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

        self.ui.eventsList.addTopLevelItem(item)
        self.ui.eventsList.resizeColumnToContents(0)
        self.ui.eventsList.resizeColumnToContents(1)

    @Slot(QTreeWidgetItem, int)
    def eventDoubleClicked(self, item, col):
        event = item.data(0, Qt.UserRole)
        self.display_contact.emit(event.contact)

# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

import requests

from PyQt5.QtGui import QIcon, QImage, QPixmap, QPixmapCache
from PyQt5.QtWidgets import QFrame, QApplication
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.applications.qcineoob.ui.miniperson_ui import Ui_MiniPerson
from weboob.capabilities.base import empty, NotAvailable


class MiniPerson(QFrame):
    def __init__(self, weboob, backend, person, parent=None):
        super(MiniPerson, self).__init__(parent)
        self.parent = parent
        self.ui = Ui_MiniPerson()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.person = person
        self.ui.nameLabel.setText('%s' % person.name)
        if not empty(person.short_description):
            if self.parent.ui.currentActionLabel.text().startswith('Casting'):
                self.ui.shortDescTitleLabel.setText(u'Role')
            self.ui.shortDescLabel.setText('%s' % person.short_description)
        else:
            self.ui.shortDescTitleLabel.hide()
            self.ui.shortDescLabel.hide()
        self.ui.backendButton.setText(backend.name)
        minfo = self.weboob.repositories.get_module_info(backend.NAME)
        icon_path = self.weboob.repositories.get_module_icon_path(minfo)
        if icon_path:
            pixmap = QPixmapCache.find(icon_path)
            if not pixmap:
                pixmap = QPixmap(QImage(icon_path))
            self.ui.backendButton.setIcon(QIcon(pixmap))

        self.ui.newTabButton.clicked.connect(self.newTabPressed)
        self.ui.viewButton.clicked.connect(self.viewPressed)
        self.ui.viewThumbnailButton.clicked.connect(self.gotThumbnail)

        if self.parent.parent.ui.showTCheck.isChecked():
            self.gotThumbnail()

    @Slot()
    def gotThumbnail(self):
        if empty(self.person.thumbnail_url) and self.person.thumbnail_url != NotAvailable:
            self.backend.fill_person(self.person, ('thumbnail_url'))
        if not empty(self.person.thumbnail_url):
            data = requests.get(self.person.thumbnail_url).content
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img).scaledToHeight(100,Qt.SmoothTransformation))

    @Slot()
    def viewPressed(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        person = self.backend.get_person(self.person.id)
        if person:
            self.parent.doAction(u'Person "%s"' %
                                 person.name, self.parent.displayPerson, [person, self.backend])

    @Slot()
    def newTabPressed(self):
        person = self.backend.get_person(self.person.id)
        self.parent.parent.newTab(u'Person "%s"' %
             person.name, self.backend, person=person)

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        if event.button() == 2:
            self.gotThumbnail()
        elif event.button() == 4:
            self.newTabPressed()
        else:
            self.viewPressed()

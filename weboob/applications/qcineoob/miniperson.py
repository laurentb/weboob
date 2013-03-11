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


from PyQt4.QtGui import QFrame, QImage, QPixmap

from weboob.tools.application.qt import QtDo
from weboob.applications.qcineoob.ui.miniperson_ui import Ui_MiniPerson

class MiniPerson(QFrame):
    def __init__(self, weboob, backend, person, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_MiniPerson()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.person = person
        self.ui.nameLabel.setText(person.name)
        #self.ui.birthdateLabel.setText(person.birth_date)
        self.ui.backendLabel.setText(backend.name)

        #self.process_thumbnail = QtDo(self.weboob, self.gotThumbnail)
        #self.process_thumbnail.do('fillobj', self.person, ['thumbnail_url'], backends=backend)

    def gotThumbnail(self, backend, person):
        if not backend:
            return

        if person.thumbnail_url:
            img = QImage.fromData(person.thumbnail.data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        person = self.backend.get_person(self.person.id)
        if person:
            self.parent.doAction(self.parent.displayPerson,[person])

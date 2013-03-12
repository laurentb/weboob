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

import urllib

from PyQt4.QtGui import QFrame, QImage, QPixmap

from weboob.applications.qcineoob.ui.miniperson_ui import Ui_MiniPerson
from weboob.capabilities.base import NotAvailable

class MiniPerson(QFrame):
    def __init__(self, weboob, backend, person, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_MiniPerson()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.person = person
        self.ui.nameLabel.setText('%s'%person.name)
        if person.short_description != NotAvailable:
            if unicode(self.parent.ui.currentActionLabel.text()).startswith('Casting'):
                self.ui.shortDescTitleLabel.setText(u'Role')
            self.ui.shortDescLabel.setText('%s'%person.short_description)
        else:
            self.ui.shortDescTitleLabel.hide()
            self.ui.shortDescLabel.hide()
        self.ui.backendLabel.setText(backend.name)

    def gotThumbnail(self, backend, person):
        if self.person.thumbnail_url != NotAvailable:
            data = urllib.urlopen(self.person.thumbnail_url).read()
            img = QImage.fromData(data)
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
            self.parent.doAction(u'Details of person "%s"'%person.name,self.parent.displayPerson,[person])

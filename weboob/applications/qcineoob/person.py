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

from PyQt4.QtCore import QUrl,Qt,SIGNAL
from PyQt4.QtGui import QFrame, QImage, QPixmap

from weboob.applications.qcineoob.ui.person_ui import Ui_Person
from weboob.capabilities.base import NotAvailable, NotLoaded

class Person(QFrame):
    def __init__(self, person, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_Person()
        self.ui.setupUi(self)

        self.connect(self.ui.filmographyButton, SIGNAL("clicked()"), self.filmography)

        self.person = person
        self.gotThumbnail()
        self.ui.nameLabel.setText(person.name)

        self.ui.realNameLabel.setText('%s'%person.real_name)
        self.ui.birthPlaceLabel.setText('%s'%person.birth_place)
        self.ui.birthDateLabel.setText(person.birth_date.isoformat())
        if person.death_date != NotAvailable:
            self.ui.deathDateLabel.setText(person.death_date.isoformat())
        else:
            self.ui.deathDateLabel.parent().hide()
        self.ui.shortBioPlain.setPlainText('%s'%person.short_biography)

    def gotThumbnail(self):
        if self.person.thumbnail_url != NotAvailable:
            data = urllib.urlopen(self.person.thumbnail_url).read()
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

    def filmography(self):
        role = None
        tosearch = self.ui.filmographyCombo.currentText()
        role_desc = ''
        if tosearch != 'all':
            role = tosearch
            role_desc = ' as %s'%role
        self.parent.doAction('Filmography of "%s"%s'%(self.person.name,role_desc),
                self.parent.filmographyAction,[self.person.id,role])

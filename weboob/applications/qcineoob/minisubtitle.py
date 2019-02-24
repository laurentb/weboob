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

from PyQt5.QtWidgets import QFrame
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QImage, QPixmap, QPixmapCache

from weboob.applications.qcineoob.ui.minisubtitle_ui import Ui_MiniSubtitle
from weboob.capabilities.base import empty


class MiniSubtitle(QFrame):
    def __init__(self, weboob, backend, subtitle, parent=None):
        super(MiniSubtitle, self).__init__(parent)
        self.parent = parent
        self.ui = Ui_MiniSubtitle()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.subtitle = subtitle
        self.ui.nameLabel.setText(subtitle.name)
        if not empty(subtitle.nb_cd):
            self.ui.nbcdLabel.setText(u'%s' % subtitle.nb_cd)
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

    @Slot()
    def viewPressed(self):
        subtitle = self.backend.get_subtitle(self.subtitle.id)
        if subtitle:
            self.parent.doAction('Subtitle "%s"' %
                                 subtitle.name, self.parent.displaySubtitle, [subtitle, self.backend])

    @Slot()
    def newTabPressed(self):
        subtitle = self.backend.get_subtitle(self.subtitle.id)
        self.parent.parent.newTab(u'Subtitle "%s"' %
             subtitle.name, self.backend, subtitle=subtitle)

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        if event.button() == 4:
            self.newTabPressed()
        else:
            self.viewPressed()

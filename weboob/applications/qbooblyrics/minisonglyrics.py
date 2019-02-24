# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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

from PyQt5.QtGui import QIcon, QImage, QPixmap, QPixmapCache
from PyQt5.QtWidgets import QFrame, QApplication
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.applications.qbooblyrics.ui.minisonglyrics_ui import Ui_MiniSonglyrics
from weboob.capabilities.base import empty


class MiniSonglyrics(QFrame):
    def __init__(self, weboob, backend, songlyrics, parent=None):
        super(MiniSonglyrics, self).__init__(parent)
        self.parent = parent
        self.ui = Ui_MiniSonglyrics()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.songlyrics = songlyrics
        self.ui.titleLabel.setText(songlyrics.title)
        if not empty(songlyrics.artist):
            if len(songlyrics.artist) > 300:
                self.ui.artistLabel.setText('%s [...]'%songlyrics.artist[:300])
            else:
                self.ui.artistLabel.setText(songlyrics.artist)
        else:
            self.ui.artistLabel.setText('')
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
        QApplication.setOverrideCursor(Qt.WaitCursor)
        songlyrics = self.backend.get_lyrics(self.songlyrics.id)
        if songlyrics:
            self.parent.doAction('Lyrics of "%s" (%s)' %
                                 (songlyrics.title, songlyrics.artist), self.parent.displaySonglyrics, [songlyrics, self.backend])

    @Slot()
    def newTabPressed(self):
        songlyrics = self.backend.get_lyrics(self.songlyrics.id)
        self.parent.parent.newTab(u'Lyrics of "%s" (%s)' %
             (songlyrics.title, songlyrics.artist), self.backend, songlyrics=songlyrics)

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

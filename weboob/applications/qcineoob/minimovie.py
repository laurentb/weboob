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
from weboob.applications.qcineoob.ui.minimovie_ui import Ui_MiniMovie

class MiniMovie(QFrame):
    def __init__(self, weboob, backend, movie, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_MiniMovie()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.movie = movie
        self.ui.titleLabel.setText(movie.original_title)
        self.ui.backendLabel.setText(backend.name)

        #self.process_thumbnail = QtDo(self.weboob, self.gotThumbnail)
        #self.process_thumbnail.do('fillobj', self.movie, ['thumbnail_url'], backends=backend)

    def gotThumbnail(self, backend, movie):
        if not backend:
            return

        if movie.thumbnail_url:
            img = QImage.fromData(movie.thumbnail.data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        movie = self.backend.get_movie(self.movie.id)
        if movie:
            self.parent.doAction(self.parent.displayMovie,[movie])

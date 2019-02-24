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

from __future__ import print_function

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame

from weboob.applications.qbooblyrics.ui.songlyrics_ui import Ui_Songlyrics
from weboob.capabilities.base import empty


class Songlyrics(QFrame):
    def __init__(self, songlyrics, backend, parent=None):
        super(Songlyrics, self).__init__(parent)
        self.parent = parent
        self.ui = Ui_Songlyrics()
        self.ui.setupUi(self)

        self.songlyrics = songlyrics
        self.backend = backend

        self.ui.idEdit.setText(u'%s@%s' % (songlyrics.id, backend.name))
        if not empty(songlyrics.title):
            self.ui.titleLabel.setText(songlyrics.title)
        if not empty(songlyrics.artist):
            self.ui.artistLabel.setText(songlyrics.artist)
        else:
            self.ui.artistLabel.parent().hide()
        if not empty(songlyrics.content):
            self.ui.lyricsPlain.setPlainText(songlyrics.content)
        else:
            self.ui.lyricsPlain.parent().hide()

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)
        self.ui.verticalLayout_2.setAlignment(Qt.AlignTop)


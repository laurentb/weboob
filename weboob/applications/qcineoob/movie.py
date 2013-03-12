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

from weboob.applications.qcineoob.ui.movie_ui import Ui_Movie
from weboob.capabilities.base import NotAvailable, NotLoaded

class Movie(QFrame):
    def __init__(self, movie, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_Movie()
        self.ui.setupUi(self)

        self.connect(self.ui.castingButton, SIGNAL("clicked()"), self.casting)
        self.connect(self.ui.torrentButton, SIGNAL("clicked()"), self.searchTorrent)

        self.movie = movie
        self.ui.titleLabel.setText(movie.original_title)
        self.ui.durationLabel.setText(unicode(movie.duration))
        self.gotThumbnail()

        if movie.other_titles != NotAvailable:
            self.ui.otherTitlesPlain.setPlainText('\n'.join(movie.other_titles))
        if movie.release_date != NotAvailable:
            self.ui.releaseDateLabel.setText(movie.release_date.isoformat())
        self.ui.durationLabel.setText('%s'%movie.duration)
        self.ui.pitchPlain.setPlainText('%s'%movie.pitch)
        self.ui.countryLabel.setText('%s'%movie.country)
        self.ui.noteLabel.setText('%s'%movie.note)

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)

    def gotThumbnail(self):
        if self.movie.thumbnail_url != NotAvailable:
            data = urllib.urlopen(self.movie.thumbnail_url).read()
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

    def searchTorrent(self):
        tosearch = self.movie.original_title
        if self.movie.release_date != NotAvailable:
            tosearch += ' %s'%self.movie.release_date.year
        desc = 'Search torrents for "%s"'%tosearch
        self.parent.doAction(desc, self.parent.searchTorrentAction,[tosearch])

    def casting(self):
        role = None
        tosearch = self.ui.castingCombo.currentText()
        role_desc = ''
        if tosearch != 'all':
            role = tosearch[:-1]
            role_desc = ' as %s'%role
        self.parent.doAction('Casting%s of movie "%s"'%(role_desc,self.movie.original_title),
                self.parent.castingAction,[self.movie.id,role])

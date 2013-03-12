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

from weboob.applications.qcineoob.ui.torrent_ui import Ui_Torrent
from weboob.capabilities.base import NotAvailable, NotLoaded

class Torrent(QFrame):
    def __init__(self, torrent, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_Torrent()
        self.ui.setupUi(self)

        #self.connect(self.ui.downloadButton, SIGNAL("clicked()"), self.download)

        self.torrent = torrent
        self.ui.nameLabel.setText(u'%s'%torrent.name)

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)

    def download(self):
        role = None
        tosearch = self.ui.castingCombo.currentText()
        role_desc = ''
        if tosearch != 'all':
            role = tosearch[:-1]
            role_desc = ' as %s'%role
        self.parent.doAction('Casting%s of movie "%s"'%(role_desc,self.movie.original_title),
                self.parent.castingAction,[self.movie.id,role])

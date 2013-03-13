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

import sys

from PyQt4.QtCore import Qt,SIGNAL
from PyQt4.QtGui import QFrame, QFileDialog

from weboob.applications.qcineoob.ui.subtitle_ui import Ui_Subtitle
from weboob.capabilities.base import NotAvailable

class Subtitle(QFrame):
    def __init__(self, subtitle, backend, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.backend = backend
        self.ui = Ui_Subtitle()
        self.ui.setupUi(self)

        self.connect(self.ui.downloadButton, SIGNAL("clicked()"), self.download)

        self.subtitle = subtitle
        self.ui.nameLabel.setText(u'%s'%subtitle.name)
        if subtitle.url != NotAvailable:
            self.ui.urlEdit.setText(u'%s'%subtitle.url)

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)

    def download(self):
        fileDial = QFileDialog(self,'Save "%s" subtitle file'%self.subtitle.name,'%s'%self.subtitle.name,'all files (*)')
        fileDial.setAcceptMode(QFileDialog.AcceptSave)
        fileDial.setLabelText(QFileDialog.Accept,'Save subtitle file')
        fileDial.setLabelText(QFileDialog.FileName,'Subtitle file name')
        ok = (fileDial.exec_() == 1)
        if not ok:
            return
        result = fileDial.selectedFiles()
        if len(result) > 0:
            dest = result[0]
            data = self.backend.get_subtitle_file(self.subtitle.id)
            try:
                with open(dest, 'w') as f:
                    f.write(data)
            except IOError, e:
                print >>sys.stderr, 'Unable to write subtitle file in "%s": %s' % (dest, e)
                return 1
            return


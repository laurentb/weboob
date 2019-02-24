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

from __future__ import print_function

from PyQt5.QtCore import Qt, pyqtSlot as Slot
from PyQt5.QtWidgets import QFrame, QFileDialog

from weboob.applications.qcineoob.ui.subtitle_ui import Ui_Subtitle
from weboob.capabilities.base import empty


class Subtitle(QFrame):
    def __init__(self, subtitle, backend, parent=None):
        super(Subtitle, self).__init__(parent)
        self.parent = parent
        self.backend = backend
        self.ui = Ui_Subtitle()
        self.ui.setupUi(self)

        self.ui.downloadButton.clicked.connect(self.download)

        self.subtitle = subtitle
        self.ui.idEdit.setText(u'%s@%s' % (subtitle.id, backend.name))
        self.ui.nameLabel.setText(u'%s' % subtitle.name)
        if not empty(subtitle.nb_cd):
            self.ui.nbcdLabel.setText(u'%s' % subtitle.nb_cd)
        else:
            self.ui.nbcdLabel.parent().hide()
        if not empty(subtitle.language):
            self.ui.langLabel.setText(u'%s' % subtitle.language)
        else:
            self.ui.langLabel.parent().hide()
        if not empty(subtitle.description):
            self.ui.descriptionPlain.setPlainText(u'%s' % subtitle.description)
        else:
            self.ui.descriptionPlain.parent().hide()
        if not empty(subtitle.url):
            self.ui.urlEdit.setText(u'%s' % subtitle.url)
        else:
            self.ui.downloadButton.setDisabled(True)
            self.ui.downloadButton.setText('Impossible to download this subtitle')

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)

    @Slot()
    def download(self):
        if not empty(self.subtitle.url):
            if self.subtitle.url.endswith('.rar'):
                ext = '.rar'
            elif self.subtitle.url.endswith('.srt'):
                ext = '.srt'
            else:
                ext = '.zip'
        fileDial = QFileDialog(self, 'Save "%s" subtitle file' %
                               self.subtitle.name, '%s%s' % (self.subtitle.name, ext), 'all files (*)')
        fileDial.setAcceptMode(QFileDialog.AcceptSave)
        fileDial.setLabelText(QFileDialog.Accept, 'Save subtitle file')
        fileDial.setLabelText(QFileDialog.FileName, 'Subtitle file name')
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
            except IOError as e:
                print('Unable to write subtitle file in "%s": %s' % (dest, e), file=self.stderr)
                return 1
            return

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

from weboob.applications.qcineoob.ui.torrent_ui import Ui_Torrent
from weboob.applications.weboorrents.weboorrents import sizeof_fmt
from weboob.capabilities.base import empty
from weboob.tools.compat import unicode


class Torrent(QFrame):
    def __init__(self, torrent, backend, parent=None):
        super(Torrent, self).__init__(parent)
        self.parent = parent
        self.backend = backend
        self.ui = Ui_Torrent()
        self.ui.setupUi(self)

        self.ui.downloadButton.clicked.connect(self.download)

        self.torrent = torrent
        self.ui.idEdit.setText(u'%s@%s' % (torrent.id, backend.name))
        self.ui.nameLabel.setText(u'%s' % torrent.name)
        if not empty(torrent.url):
            self.ui.urlEdit.setText(u'%s' % torrent.url)
        else:
            self.ui.urlFrame.hide()
            self.ui.downloadButton.setDisabled(True)
            if not empty(torrent.magnet):
                self.ui.downloadButton.setText(u'Download not available\nbut magnet link provided')
                self.ui.downloadButton.setToolTip(u'Use the magnet link')
        if not empty(torrent.description):
            self.ui.descriptionPlain.setText(u'%s' % torrent.description)
        else:
            self.ui.descriptionPlain.parent().hide()
        if not empty(torrent.files):
            files = u''
            for f in torrent.files:
                files += '%s\n' % f
            self.ui.filesPlain.setText(u'%s' % files)
        else:
            self.ui.filesPlain.parent().hide()
        if not empty(torrent.magnet):
            self.ui.magnetEdit.setText(u'%s' % torrent.magnet)
        else:
            self.ui.magnetFrame.hide()
        if not empty(torrent.seeders) and not empty(torrent.leechers):
            self.ui.seedLeechLabel.setText(u'%s/%s' % (torrent.seeders, torrent.leechers))
        if not empty(torrent.size):
            self.ui.sizeLabel.setText(u'%s' % sizeof_fmt(torrent.size))

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)

    @Slot()
    def download(self):
        fileDial = QFileDialog(self, 'Save "%s" torrent file' % self.torrent.name, '%s.torrent' %
                               self.torrent.name, 'Torrent file (*.torrent);;all files (*)')
        fileDial.setAcceptMode(QFileDialog.AcceptSave)
        fileDial.setLabelText(QFileDialog.Accept, 'Save torrent file')
        fileDial.setLabelText(QFileDialog.FileName, 'Torrent file name')
        ok = (fileDial.exec_() == 1)
        if not ok:
            return
        result = fileDial.selectedFiles()
        if len(result) > 0:
            dest = result[0]
            data = self.backend.get_torrent_file(self.torrent.id)
            try:
                with open(unicode(dest), 'w') as f:
                    f.write(data)
            except IOError as e:
                print('Unable to write .torrent in "%s": %s' % (dest, e), file=self.stderr)
                return 1
            return

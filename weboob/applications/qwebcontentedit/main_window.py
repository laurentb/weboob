# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from PyQt4.QtCore import SIGNAL


from weboob.tools.application.qt import QtMainWindow, QtDo

from .ui.main_window_ui import Ui_MainWindow

class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.backend = None

        self.connect(self.ui.idEdit, SIGNAL("returnPressed()"), self.loadPage)
        self.connect(self.ui.loadButton, SIGNAL("clicked()"), self.loadPage)
        self.connect(self.ui.tabWidget, SIGNAL("currentChanged(int)"),
self._currentTabChanged)
        self.connect(self.ui.saveButton, SIGNAL("clicked()"), self.savePage)

    def _currentTabChanged(self):
        if self.ui.tabWidget.currentIndex() == 1:
            if self.backend is not None:
                self.showPreview()
        return

    def loadPage(self):
        _id = unicode(self.ui.idEdit.text())
        if not _id:
            return

        for backend in self.weboob.iter_backends():
            self.content = backend.get_content(_id)
            if self.content:
                self.ui.contentEdit.setPlainText(self.content.content)
                self.backend = backend
                return


    def savePage(self):
        if self.backend is None:
            return
        new_content = unicode(self.ui.contentEdit.toPlainText())
        if new_content != self.content.content:
            self.content.content = new_content
            message = unicode(self.ui.descriptionEdit.text())
            self.process = QtDo(self.weboob, self._savePage_cb, self._savePage_eb)
            self.process.do('push_content', self.content, message, backends=self.backend)

    def _savePage_cb(self, backend, data):
        if not backend:
            return
        self.ui.descriptionEdit.clear()

    def _savePage_eb(self, backend, error, backtrace):
        print error
        print backtrace

    def showPreview(self):
        self.ui.previewEdit.setHtml(self.backend.get_content_preview(self.content))
        return
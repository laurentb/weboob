# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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

import logging
from copy import deepcopy
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMessageBox

from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.content import ICapContent
from weboob.tools.misc import to_unicode

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
        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()
        else:
            self.loadBackends()

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (ICapContent,), self)
        if bckndcfg.run():
            self.loadBackends()

    def loadBackends(self):
        self.ui.backendBox.clear()
        for backend in self.weboob.iter_backends():
            self.ui.backendBox.insertItem(0, backend.name)

    def _currentTabChanged(self):
        if self.ui.tabWidget.currentIndex() == 1:
            if self.backend is not None:
                self.showPreview()

    def loadPage(self):
        _id = unicode(self.ui.idEdit.text())
        if not _id:
            return
        self.ui.saveButton.setEnabled(False)
        backend = str(self.ui.backendBox.currentText())
        self.process = QtDo(self.weboob, self._loadPage_cb, self._loadPage_eb)
        self.process.do('get_content', _id, backends=(backend,))

    def _loadPage_cb(self, backend, data):
        if not backend:
            self.process = None
            if self.backend:
                self.ui.saveButton.setEnabled(True)
            return
        if not data:
            self.content = None
            self.backend = None
            QMessageBox.critical(self, self.tr('Unable to open page'),
                                 'Unable to open page "%s" on %s: it does not exist.'
                                 % (self.ui.idEdit.text(), self.ui.backendBox.currentText()),
                                 QMessageBox.Ok)
            return

        self.content = data
        self.ui.contentEdit.setPlainText(self.content.content)
        self.setWindowTitle("QWebcontentedit - %s@%s" %(self.content.id, backend.name))
        self.backend = backend

    def _loadPage_eb(self, backend, error, backtrace):
        content = unicode(self.tr('Unable to load page:\n%s\n')) % to_unicode(error)
        if logging.root.level == logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while loading page'),
                             content, QMessageBox.Ok)

    def savePage(self):
        if self.backend is None:
            return
        new_content = unicode(self.ui.contentEdit.toPlainText())
        minor = self.ui.minorBox.isChecked()
        if new_content != self.content.content:
            self.ui.saveButton.setEnabled(False)
            self.content.content = new_content
            message = unicode(self.ui.descriptionEdit.text())
            self.process = QtDo(self.weboob, self._savePage_cb, self._savePage_eb)
            self.process.do('push_content', self.content, message, minor=minor, backends=self.backend)

    def _savePage_cb(self, backend, data):
        if not backend:
            self.process = None
            self.ui.saveButton.setEnabled(True)
            return
        self.ui.descriptionEdit.clear()

    def _savePage_eb(self, backend, error, backtrace):
        content = unicode(self.tr('Unable to save page:\n%s\n')) % to_unicode(error)
        if logging.root.level == logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while saving page'),
                             content, QMessageBox.Ok)
        self.ui.saveButton.setEnabled(True)

    def showPreview(self):
        tmp_content = deepcopy(self.content)
        tmp_content.content=unicode(self.ui.contentEdit.toPlainText())
        self.ui.previewEdit.setHtml(self.backend.get_content_preview(tmp_content))

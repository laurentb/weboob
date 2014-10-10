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
from PyQt4.QtGui import QMessageBox, QTableWidgetItem
from PyQt4.QtCore import Qt

from weboob.tools.application.base import MoreResultsAvailable
from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.content import CapContent
from weboob.tools.misc import to_unicode

from .ui.main_window_ui import Ui_MainWindow


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, app, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.backend = None
        self.app = app

        self.connect(self.ui.idEdit,
                     SIGNAL("returnPressed()"),
                     self.loadPage)
        self.connect(self.ui.loadButton,
                     SIGNAL("clicked()"),
                     self.loadPage)
        self.connect(self.ui.tabWidget,
                     SIGNAL("currentChanged(int)"),
                     self._currentTabChanged)
        self.connect(self.ui.saveButton,
                     SIGNAL("clicked()"),
                     self.savePage)
        self.connect(self.ui.actionBackends,
                     SIGNAL("triggered()"),
                     self.backendsConfig)
        self.connect(self.ui.contentEdit,
                     SIGNAL("textChanged()"),
                     self._textChanged)
        self.connect(self.ui.loadHistoryButton,
                     SIGNAL("clicked()"),
                     self.loadHistory)

        if hasattr(self.ui.descriptionEdit, "setPlaceholderText"):
            self.ui.descriptionEdit.setPlaceholderText("Edit summary")

        if self.weboob.count_backends() == 0:
            self.backendsConfig()
        else:
            self.loadBackends()

    def backendsConfig(self):
        """ Opens backends configuration dialog when 'Backends' is clicked """
        bckndcfg = BackendCfg(self.weboob, (CapContent,), self)
        if bckndcfg.run():
            self.loadBackends()

    def loadBackends(self):
        """ Fills the backends comboBox with available backends """
        self.ui.backendBox.clear()
        for backend in self.weboob.iter_backends():
            self.ui.backendBox.insertItem(0, backend.name)

    def _currentTabChanged(self):
        """ Loads history or preview when the corresponding tabs are shown """
        if self.ui.tabWidget.currentIndex() == 1:
            if self.backend is not None:
                self.loadPreview()
        elif self.ui.tabWidget.currentIndex() == 2:
            if self.backend is not None:
                self.loadHistory()

    def _textChanged(self):
        """ The text in the content QPlainTextEdit has changed """
        if self.backend:
            self.ui.saveButton.setEnabled(True)
            self.ui.saveButton.setText('Save')

    def loadPage(self):
        """ Loads a page's source into the 'content' QPlainTextEdit """
        _id = unicode(self.ui.idEdit.text())
        if not _id:
            return

        self.ui.loadButton.setEnabled(False)
        self.ui.loadButton.setText('Loading...')
        self.ui.contentEdit.setReadOnly(True)

        backend = str(self.ui.backendBox.currentText())

        def finished():
            self.process = None
            if self.backend:
                self.ui.contentEdit.setReadOnly(False)
                self.ui.loadButton.setEnabled(True)
                self.ui.loadButton.setText('Load')

        self.process = QtDo(self.weboob,
                            self._loadedPage,
                            self._errorLoadPage,
                            finished)
        self.process.do('get_content', _id, backends=(backend,))

    def _loadedPage(self, data):
        """ Callback for loadPage """
        if not data:
            self.content = None
            self.backend = None
            QMessageBox.critical(self, self.tr('Unable to open page'),
                                 'Unable to open page "%s" on %s: it does not exist.'
                                 % (self.ui.idEdit.text(),
                                    self.ui.backendBox.currentText()),
                                 QMessageBox.Ok)
            return

        self.content = data
        self.ui.contentEdit.setPlainText(self.content.content)
        self.setWindowTitle("QWebcontentedit - %s@%s" %(self.content.id,
                                                        self.content.backend))
        self.backend = self.weboob[self.content.backend]

    def _errorLoadPage(self, backend, error, backtrace):
        """ Error callback for loadPage """
        content = unicode(self.tr('Unable to load page:\n%s\n')) % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while loading page'),
                             content, QMessageBox.Ok)
        self.ui.loadButton.setEnabled(True)
        self.ui.loadButton.setText("Load")

    def savePage(self):
        """ Saves the current page to the remote site """
        if self.backend is None:
            return
        new_content = unicode(self.ui.contentEdit.toPlainText())
        minor = self.ui.minorBox.isChecked()
        if new_content != self.content.content:
            self.ui.saveButton.setEnabled(False)
            self.ui.saveButton.setText('Saving...')
            self.ui.contentEdit.setReadOnly(True)
            self.content.content = new_content
            message = unicode(self.ui.descriptionEdit.text())

            def finished():
                self.process = None
                self.ui.saveButton.setText('Saved')
                self.ui.descriptionEdit.clear()
                self.ui.contentEdit.setReadOnly(False)

            self.process = QtDo(self.weboob,
                                None,
                                self._errorSavePage,
                                finished)
            self.process.do('push_content',
                            self.content,
                            message,
                            minor=minor,
                            backends=self.backend)

    def _errorSavePage(self, backend, error, backtrace):
        """ """
        content = unicode(self.tr('Unable to save page:\n%s\n')) % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while saving page'),
                             content, QMessageBox.Ok)
        self.ui.saveButton.setEnabled(True)
        self.ui.saveButton.setText("Save")

    def loadPreview(self):
        """ Loads the current page's preview into the preview QTextEdit """
        tmp_content = deepcopy(self.content)
        tmp_content.content = unicode(self.ui.contentEdit.toPlainText())
        self.ui.previewEdit.setHtml(self.backend.get_content_preview(tmp_content))

    def loadHistory(self):
        """ Loads the page's log into the 'History' tab """
        if self.backend is None:
            return

        self.ui.loadHistoryButton.setEnabled(False)
        self.ui.loadHistoryButton.setText("Loading...")

        self.ui.historyTable.clear()
        self.ui.historyTable.setRowCount(0)

        self.ui.historyTable.setHorizontalHeaderLabels(["Revision",
                                                        "Time",
                                                        "Author",
                                                        "Summary"])
        self.ui.historyTable.setColumnWidth(3, 1000)

        def finished():
            self.process = None
            self.ui.loadHistoryButton.setEnabled(True)
            self.ui.loadHistoryButton.setText("Reload")


        self.process = QtDo(self.weboob,
                            self._gotRevision,
                            self._errorHistory,
                            finished)
        self.process.do(self.app._do_complete,
                        self.ui.nbRevBox.value(),
                        (),
                        'iter_revisions',
                        self.content.id,
                        backends=(self.backend,))

    def _gotRevision(self, revision):
        """ Callback for loadHistory's QtDo """
        # we set the flags to Qt.ItemIsEnabled so that the items
        # are not modifiable (they are modifiable by default)
        item_revision = QTableWidgetItem(revision.id)
        item_revision.setFlags(Qt.ItemIsEnabled)

        item_time = QTableWidgetItem(revision.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        item_time.setFlags(Qt.ItemIsEnabled)

        item_author = QTableWidgetItem(revision.author)
        item_author.setFlags(Qt.ItemIsEnabled)

        item_summary = QTableWidgetItem(revision.comment)
        item_summary.setFlags(Qt.ItemIsEnabled)

        row = self.ui.historyTable.currentRow() + 1
        self.ui.historyTable.insertRow(row)
        self.ui.historyTable.setItem(row, 0, item_revision)
        self.ui.historyTable.setItem(row, 1, item_time)
        self.ui.historyTable.setItem(row, 2, item_author)
        self.ui.historyTable.setItem(row, 3, item_summary)

        self.ui.historyTable.setCurrentCell(row, 0)

    def _errorHistory(self, backend, error, backtrace):
        """ Loading the history has failed """
        if isinstance(error, MoreResultsAvailable):
            return

        content = unicode(self.tr('Unable to load history:\n%s\n')) % to_unicode(error)
        if logging.root.level <= logging.DEBUG:
            content += '\n%s\n' % to_unicode(backtrace)
        QMessageBox.critical(self, self.tr('Error while loading history'),
                             content, QMessageBox.Ok)

        self.ui.loadHistoryButton.setEnabled(True)
        self.ui.loadHistoryButton.setText("Reload")

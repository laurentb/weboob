# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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

from PyQt5.QtWidgets import QDialog, QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.tools.application.qt5 import QtDo, HTMLDelegate
from weboob.tools.compat import range

from .ui.query_ui import Ui_QueryDialog


class QueryDialog(QDialog):
    def __init__(self, weboob, parent=None):
        super(QueryDialog, self).__init__(parent)
        self.ui = Ui_QueryDialog()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.ui.resultsList.setItemDelegate(HTMLDelegate())
        self.ui.citiesList.setItemDelegate(HTMLDelegate())

        self.search_process = None

        self.ui.cityEdit.returnPressed.connect(self.searchCity)
        self.ui.resultsList.itemDoubleClicked.connect(self.insertCity)
        self.ui.citiesList.itemDoubleClicked.connect(self.removeCity)
        self.ui.buttonBox.accepted.connect(self.okButton)

        if hasattr(self.ui.cityEdit, "setPlaceholderText"):
            self.ui.cityEdit.setPlaceholderText("Press enter to search city")

    def keyPressEvent(self, event):
        """
        Disable handler <Enter> and <Escape> to prevent closing the window.
        """
        event.ignore()

    def selectComboValue(self, box, value):
        for i in range(box.count()):
            if box.itemText(i) == str(value):
                box.setCurrentIndex(i)
                break

    @Slot()
    def searchCity(self):
        pattern = self.ui.cityEdit.text()
        self.ui.resultsList.clear()
        self.ui.cityEdit.clear()
        self.ui.cityEdit.setEnabled(False)

        self.search_process = QtDo(self.weboob, self.addResult, fb=self.addResultEnd)
        self.search_process.do('search_city', pattern)

    def addResultEnd(self):
        self.search_process = None
        self.ui.cityEdit.setEnabled(True)

    def addResult(self, city):
        if not city:
            return
        item = self.buildCityItem(city)
        self.ui.resultsList.addItem(item)
        self.ui.resultsList.sortItems()

    def buildCityItem(self, city):
        item = QListWidgetItem()
        item.setText('<b>%s</b> (%s)' % (city.name, city.backend))
        item.setData(Qt.UserRole, city)
        return item

    @Slot(QListWidgetItem)
    def insertCity(self, i):
        item = QListWidgetItem()
        item.setText(i.text())
        item.setData(Qt.UserRole, i.data(Qt.UserRole))
        self.ui.citiesList.addItem(item)

    @Slot(QListWidgetItem)
    def removeCity(self, item):
        self.ui.citiesList.removeItemWidget(item)

    @Slot()
    def okButton(self):
        if not self.ui.nameEdit.text():
            QMessageBox.critical(self, self.tr('Error'), self.tr('Please enter a name to your query.'), QMessageBox.Ok)
            return

        if self.ui.citiesList.count() == 0:
            QMessageBox.critical(self, self.tr('Error'), self.tr('Please add at least one city.'), QMessageBox.Ok)
            return

        self.accept()

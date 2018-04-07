# -*- coding: utf-8 -*-

# Copyright(C) 2016 Vincent A
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

import os

from PyQt5.QtCore import Qt, QModelIndex, pyqtSlot as Slot
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication

from weboob.tools.application.qt5 import QtMainWindow
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.tools.application.qt5.models import BackendListModel, ResultModel, FilterTypeModel
from weboob.tools.compat import range
from weboob.capabilities.collection import BaseCollection, CapCollection
from weboob.capabilities.gallery import CapGallery, BaseGallery
from weboob.capabilities.image import CapImage, BaseImage

from .ui.mainwindow_ui import Ui_MainWindow
from .viewer import Viewer


def size_format(n):
    UNITS = [
        (1 << 40, 'TiB'),
        (1 << 30, 'GiB'),
        (1 << 20, 'MiB'),
        (1 << 10, 'KiB'),
        (0, 'B')
    ]
    for f, u in UNITS:
        if n > f:
            return '%.2f %s' % (n / float(f), u)


class MainWindow(QtMainWindow):
    def __init__(self, config, storage, weboob, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.mdl = ResultModel(weboob)
        self.mdl.setColumnFields([['name', 'title'],['url']])
        self.mdl.jobAdded.connect(self._jobAdded)
        self.mdl.jobFinished.connect(self._jobFinished)
        self.proxy_mdl = FilterTypeModel()
        self.proxy_mdl.setAcceptedTypes([BaseCollection, BaseGallery])
        self.proxy_mdl.setSourceModel(self.mdl)

        self.ui.collectionTree.setModel(self.proxy_mdl)
        self.ui.collectionTree.selectionModel().currentChanged.connect(self.showCollection)
        n = self.mdl.columnCount(QModelIndex())
        for i in range(n):
            self.ui.collectionTree.setColumnWidth(i, self.ui.collectionTree.width() // n)

        self.config = config
        self.storage = storage
        self.weboob = weboob

        self.ui.browseButton.clicked.connect(self.startBrowse)

        self.ui.searchGallEdit.returnPressed.connect(self.startGallSearch)
        self.ui.searchGallButton.clicked.connect(self.startGallSearch)

        self.ui.searchImgEdit.returnPressed.connect(self.startImgSearch)
        self.ui.searchImgButton.clicked.connect(self.startImgSearch)

        self.ui.imageList.setModel(self.mdl)
        self.ui.imageList.selectionModel().currentChanged.connect(self.showImageInfo)
        self.ui.imageList.activated.connect(self.openImage)

        self.fillBackends()

        if self.weboob.count_backends() == 0:
            self.backendsConfig()
        self.ui.actionBackends.triggered.connect(self.backendsConfig)

        self.ui.limitResults.valueChanged.connect(self._limitResultsChanged)
        self.mdl.setLimit(self.ui.limitResults.value())

        self.lastSaveDir = os.path.expanduser('~')

    @Slot()
    def backendsConfig(self):
        cfg = BackendCfg(self.weboob, (CapImage,), self)
        if cfg.run():
            self.fillBackends()

    def fillBackends(self):
        model = BackendListModel(self.weboob)
        model.addBackends(CapGallery)
        self.ui.backendGallCombo.setModel(model)

        model = BackendListModel(self.weboob)
        model.addBackends(CapImage)
        self.ui.backendImgCombo.setModel(model)

        model = BackendListModel(self.weboob)
        model.addBackends(CapImage, entry_title=True)
        model.addBackends(CapGallery, entry_title=True)
        self.ui.backendCollCombo.setModel(model)

    @Slot()
    def changeBackend(self):
        cap, backend = self.selectedBackend()

        if cap is CapImage:
            res_class = BaseImage
        else:
            res_class = BaseGallery
        self.mdl.setResourceClasses([res_class])

    @Slot(QModelIndex)
    def showCollection(self, qidx):
        qidx = self.proxy_mdl.mapToSource(qidx)
        qidx = qidx.sibling(qidx.row(), 0)
        self.ui.imageList.setRootIndex(qidx)

    @Slot(QModelIndex)
    def showGallery(self, qidx):
        self.ui.imageList.setEnabled(True)
        self.ui.imageList.show()
        qidx = qidx.sibling(qidx.row(), 0)
        self.ui.imageList.setRootIndex(qidx)

    def showNoneItem(self):
        self.ui.labelTitle.setText('-')
        self.ui.labelDescription.setText('-')
        self.ui.labelAuthor.setText('-')
        self.ui.labelDate.setText('-')
        self.ui.labelLink.setText('-')
        self.ui.labelSize.setText('-')
        self.ui.labelRating.setText('-')

    @Slot(QModelIndex)
    def showImageInfo(self, qidx):
        obj = qidx.data(ResultModel.RoleObject)
        if obj is None:
            self.showNoneItem()
            return

        if isinstance(obj, BaseImage):
            self.ui.labelTitle.setText(obj.title or '')
            self.ui.labelDescription.setText(obj.description or '')
            self.ui.labelAuthor.setText(obj.author or '')
            if obj.size:
                self.ui.labelSize.setText(size_format(obj.size) or '')
            else:
                self.ui.labelSize.setText('-')
            if obj.url:
                self.ui.labelLink.setText('<a href="%s">Link</a>' % obj.url)
            else:
                self.ui.labelLink.setText('')
        elif isinstance(obj, BaseGallery):
            pass

    @Slot(QModelIndex)
    def openImage(self, qidx):
        obj = qidx.data(ResultModel.RoleObject)

        if isinstance(obj, BaseImage):
            viewer = Viewer(self.weboob, self)
            viewer.jobAdded.connect(self._jobAdded)
            viewer.jobFinished.connect(self._jobFinished)
            viewer.setData(self.mdl, qidx)
            viewer.show()
        elif isinstance(obj, BaseGallery):
            self.ui.imageList.setRootIndex(qidx)

            qidx = self.proxy_mdl.mapFromSource(qidx)
            self.ui.collectionTree.setCurrentIndex(qidx)

    @Slot()
    def startImgSearch(self):
        backend = self.ui.backendImgCombo.currentData(BackendListModel.RoleBackendName)
        if not backend:
            backend = list(self.weboob.iter_backends(caps=CapImage))

        pattern = self.ui.searchImgEdit.text()
        if not pattern:
            return

        self.mdl.clear()

        self.ui.imageList.setRootIndex(QModelIndex())
        self.ui.collectionTree.setRootIndex(QModelIndex())
        self.mdl.addRootDoLimit(BaseImage, 'search_image', pattern, backends=backend)

    @Slot()
    def startGallSearch(self):
        backend = self.ui.backendGallCombo.currentData(BackendListModel.RoleBackendName)
        if not backend:
            backend = list(self.weboob.iter_backends(caps=CapGallery))

        pattern = self.ui.searchGallEdit.text()
        if not pattern:
            return

        self.mdl.clear()

        self.ui.imageList.setRootIndex(QModelIndex())
        self.ui.collectionTree.setRootIndex(QModelIndex())
        self.mdl.addRootDoLimit(BaseGallery, 'search_galleries', pattern, backends=backend)

    @Slot()
    def startBrowse(self):
        self.mdl.clear()

        cap = self.ui.backendCollCombo.currentData(BackendListModel.RoleCapability)
        backend = self.ui.backendCollCombo.currentData(BackendListModel.RoleBackendName)
        if backend:
            backends = [backend]
        else:
            backends = [b for b in self.weboob.iter_backends(caps=(cap,)) if b.has_caps(CapCollection)]

        res_classes = [BaseImage, BaseGallery]
        self.mdl.setResourceClasses(res_classes)

        self.mdl.addRootDoLimit(None, 'iter_resources', res_classes, [], backends=backends)

    @Slot()
    def _jobAdded(self):
        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))

    @Slot()
    def _jobFinished(self):
        QApplication.restoreOverrideCursor()

    @Slot(int)
    def _limitResultsChanged(self, value):
        self.mdl.setLimit(value)

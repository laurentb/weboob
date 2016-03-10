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
        self.proxy_mdl.setAcceptedTypes([BaseCollection])
        self.proxy_mdl.setSourceModel(self.mdl)

        self.ui.collectionTree.setModel(self.proxy_mdl)
        self.ui.collectionTree.selectionModel().currentChanged.connect(self.showCollection)

        self.config = config
        self.storage = storage
        self.weboob = weboob

        self.ui.browseButton.clicked.connect(self.startBrowse)
        self.ui.searchEdit.returnPressed.connect(self.startSearch)
        self.ui.searchButton.clicked.connect(self.startSearch)
        self.ui.galleryList.setModel(self.mdl)
        self.ui.galleryList.selectionModel().currentChanged.connect(self.showGallery)
        self.ui.galleryList.hide()

        self.ui.imageList.setModel(self.mdl)
        self.ui.imageList.selectionModel().currentChanged.connect(self.showImageInfo)
        self.ui.imageList.activated.connect(self.openImage)

        # backendEdit choice

        self.fillBackends()
        self.ui.backendEdit.currentIndexChanged.connect(self.changeBackend)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()
        self.ui.actionBackends.triggered.connect(self.backendsConfig)

        self.lastSaveDir = os.path.expanduser('~')

    @Slot()
    def backendsConfig(self):
        cfg = BackendCfg(self.weboob, (CapImage,), self)
        if cfg.run():
            self.fillBackends()

    def fillBackends(self):
        model = BackendListModel(self.weboob)
        model.addBackends(CapGallery, entry_title=True)
        model.addBackends(CapImage, entry_title=True)
        self.ui.backendEdit.setModel(model)

    def selectedBackend(self):
        cap = self.ui.backendEdit.currentData(BackendListModel.RoleCapability)
        backend = self.ui.backendEdit.currentData(BackendListModel.RoleBackendName)
        return cap, backend

    def _collectionBackends(self):
        cap, backend = self.selectedBackend()
        if backend is not None:
            return [backend]

        backends = self.weboob.iter_backends(caps=cap)
        return [b for b in backends if b.has_caps(CapCollection)]

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
        cap, _ = self.selectedBackend()

        qidx = self.proxy_mdl.mapToSource(qidx)
        qidx = qidx.sibling(qidx.row(), 0)
        if cap is CapImage:
            self.ui.galleryList.hide()
            self.ui.imageList.setRootIndex(qidx)
            self.ui.imageList.setEnabled(True)
            self.ui.imageList.show()
        else:
            self.ui.galleryList.show()
            self.ui.galleryList.setRootIndex(qidx)
            self.ui.galleryList.setEnabled(True)

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
        image = qidx.data(self.mdl.RoleObject)
        if image is None:
            self.showNoneItem()
            return

        self.ui.labelTitle.setText(image.title or '')
        self.ui.labelDescription.setText(image.description or '')
        self.ui.labelAuthor.setText(image.author or '')
        if image.size:
            self.ui.labelSize.setText(size_format(image.size) or '')
        else:
            self.ui.labelSize.setText('-')
        if image.url:
            self.ui.labelLink.setText('<a href="%s">Link</a>' % image.url)
        else:
            self.ui.labelLink.setText('')

    @Slot(QModelIndex)
    def openImage(self, qidx):
        viewer = Viewer(self.weboob, self)
        viewer.jobAdded.connect(self._jobAdded)
        viewer.jobFinished.connect(self._jobFinished)
        viewer.setData(self.mdl, qidx)
        viewer.show()

    @Slot()
    def startSearch(self):
        pattern = self.ui.searchEdit.text()
        if not pattern:
            return

        self.mdl.clear()
        cap, backend = self.selectedBackend()
        if cap is CapImage:
            self.ui.galleryList.hide()
            self.ui.imageList.setRootIndex(QModelIndex())
            self.mdl.addRootDo('search_image', pattern, backends=backend)
            self.ui.imageList.setEnabled(True)
            self.ui.imageList.show()
        elif cap is CapGallery:
            self.ui.imageList.hide()
            self.ui.galleryList.setRootIndex(QModelIndex())
            self.mdl.addRootDo('search_galleries', pattern, backends=backend)
            self.ui.galleryList.setEnabled(True)
            self.ui.galleryList.show()

    @Slot()
    def startBrowse(self):
        self.ui.collectionTree.setEnabled(True)
        self.ui.galleryList.setEnabled(False)
        self.ui.imageList.setEnabled(False)

        self.mdl.clear()

        cap, backend = self.selectedBackend()
        if cap is CapImage:
            self.ui.galleryList.hide()
            res_class = BaseImage
        else:
            self.ui.galleryList.show()
            res_class = BaseGallery
        self.mdl.setResourceClasses([res_class])

        backends = self._collectionBackends()
        self.mdl.addRootDo('iter_resources', [res_class], [], backends=backends)

    @Slot()
    def _jobAdded(self):
        QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))

    @Slot()
    def _jobFinished(self):
        QApplication.restoreOverrideCursor()

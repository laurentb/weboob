# -*- coding: utf-8 -*-

# Copyright(C) 2016 Vincent A
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

import os
import re

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt, pyqtSlot as Slot, pyqtSignal as Signal, QModelIndex, QPersistentModelIndex

from weboob.tools.application.qt5 import QtMainWindow
from weboob.tools.application.qt5.models import ResultModel
from weboob.capabilities.base import NotLoaded

from .ui.viewer_ui import Ui_Viewer


ZOOM_FACTOR, ZOOM_FIT = range(2)


class Viewer(QtMainWindow):
    jobAdded = Signal()
    jobFinished = Signal()

    def __init__(self, weboob, parent=None):
        super(Viewer, self).__init__(parent)

        self.ui = Ui_Viewer()
        self.ui.setupUi(self)
        self.ui.prevButton.clicked.connect(self.prev)
        self.ui.nextButton.clicked.connect(self.next)
        self.ui.firstButton.clicked.connect(self.first)
        self.ui.lastButton.clicked.connect(self.last)
        self.ui.actionZoomIn.triggered.connect(self.zoomIn)
        self.ui.actionZoomOut.triggered.connect(self.zoomOut)
        self.ui.actionFullSize.triggered.connect(self.zoomFullSize)
        self.ui.actionFitWindow.triggered.connect(self.zoomFit)

        self.ui.actionSaveImage.setShortcut(QKeySequence.Save)
        self.ui.actionSaveImage.triggered.connect(self.saveImage)
        self.ui.actionClose.setShortcut(QKeySequence.Close)
        self.ui.actionClose.triggered.connect(self.close)

        self.model = None
        self.current = None
        self.total = 0
        self.zoomFactor = 1
        self.zoomMode = ZOOM_FACTOR
        self.weboob = weboob

    def setData(self, model, qidx):
        self.model = model
        self.current = QPersistentModelIndex(qidx)

        self.model.rowsInserted.connect(self.updatePos)
        self.model.rowsRemoved.connect(self.updatePos)
        self.model.rowsInserted.connect(self.updateNavButtons)
        self.model.rowsRemoved.connect(self.updateNavButtons)
        self.model.dataChanged.connect(self._dataChanged)
        self.model.modelReset.connect(self.disable)

        self.updateImage()

    @Slot()
    def disable(self):
        self.setEnabled(False)

    def updateNavButtons(self):
        prev = self.current.row() > 0
        self.ui.prevButton.setEnabled(prev)
        self.ui.firstButton.setEnabled(prev)
        next = self.current.row() < self.total - 1
        self.ui.nextButton.setEnabled(next)
        self.ui.lastButton.setEnabled(next)

    def updatePos(self):
        self.total = self.model.rowCount(self.current.parent())
        self.ui.posLabel.setText('%d / %d' % (self.current.row() + 1, self.total))

    def updateImage(self):
        self.updatePos()
        self.updateNavButtons()

        obj = self.current.data(ResultModel.RoleObject)

        if obj.data is NotLoaded:
            self.model.fillObj(obj, ['data'], QModelIndex(self.current))
            self.pixmap = None
        elif obj.data:
            self.pixmap = QPixmap(QImage.fromData(obj.data))
        else:
            self.pixmap = QPixmap()

        self._rebuildImage()

    @Slot(QModelIndex)
    def _dataChanged(self, qidx):
        if qidx == self.current:
            obj = qidx.data(ResultModel.RoleObject)

            if obj.data:
                self.pixmap = QPixmap(QImage.fromData(obj.data))
            else:
                self.pixmap = QPixmap()
            self._rebuildImage()

    @Slot()
    def next(self):
        new = self.current.sibling(self.current.row() + 1, 0)
        if not new.isValid():
            return
        self.current = QPersistentModelIndex(new)
        self.updateImage()

    @Slot()
    def prev(self):
        if self.current.row() == 0:
            return
        self.current = QPersistentModelIndex(self.current.sibling(self.current.row() - 1, 0))
        self.updateImage()

    @Slot()
    def first(self):
        self.current = QPersistentModelIndex(self.current.sibling(0, 0))
        self.updateImage()

    @Slot()
    def last(self):
        self.current = QPersistentModelIndex(self.current.sibling(self.total - 1, 0))
        self.updateImage()

    @Slot()
    def zoomIn(self):
        self.zoomFactor *= 1.25
        self.zoomMode = ZOOM_FACTOR
        self._rebuildImage()

    @Slot()
    def zoomOut(self):
        self.zoomFactor *= 0.75
        self.zoomMode = ZOOM_FACTOR
        self._rebuildImage()

    @Slot()
    def zoomFullSize(self):
        self.zoomFactor = 1
        self.zoomMode = ZOOM_FACTOR
        self._rebuildImage()

    @Slot()
    def zoomFit(self):
        self.zoomMode = ZOOM_FIT
        self._rebuildImage()

    def resizeEvent(self, ev):
        super(Viewer, self).resizeEvent(ev)
        if self.zoomMode == ZOOM_FIT:
            self._rebuildImage()

    def _rebuildZoom(self):
        if self.zoomMode == ZOOM_FACTOR:
            new_width = int(self.pixmap.width() * self.zoomFactor)
            pixmap = self.pixmap.scaledToWidth(new_width, Qt.SmoothTransformation)
        else:
            new_size = self.ui.scrollArea.viewport().size()
            pixmap = self.pixmap.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.zoomFactor = pixmap.width() / float(self.pixmap.width())
        return pixmap

    def _rebuildImage(self):
        if self.pixmap is None:
            self.ui.view.setText('Loading...')
            return
        elif self.pixmap.isNull():
            self.ui.view.setText('Image could not be loaded')
            return

        pixmap = self._rebuildZoom()
        self.ui.view.setPixmap(pixmap)

    @Slot()
    def saveImage(self):
        def ext_for_filter(s):
            return re.match(r'(?:[A-Z]+) \(\*\.([a-z]+)\)$', s).group(1)

        if not self.pixmap:
            return

        filters = ['PNG (*.png)', 'JPEG (*.jpg)', 'GIF (*.gif)']

        obj = self.current.data(ResultModel.RoleObject)
        name = '%s.%s' % (obj.title or obj.id or u'', obj.ext or 'png')
        default = filters[0]
        for f in filters:
            if name.endswith(ext_for_filter(f)):
                default = f
        filters = ';;'.join(filters)

        target = os.path.join(self.parent().lastSaveDir, name)
        out, filter = QFileDialog.getSaveFileName(self, 'Save image', target, filters, default)
        if not out:
            return

        ext = ext_for_filter(filter)

        self.parent().lastSaveDir = os.path.dirname(out)
        if not os.path.splitext(out)[1]:
            out = '%s.%s' % (out, ext)

            if os.path.exists(out):
                q = self.tr('%s already exists, are you sure you want to replace it?') % out
                reply = QMessageBox.question(self, self.tr('Overwrite?'), q)
                if reply == QMessageBox.No:
                    return self.saveImage()

        self.pixmap.save(out, ext.upper())

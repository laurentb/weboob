# -*- coding: utf-8 -*-

# Copyright(C) 2010-2016  weboob project
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

from collections import deque
from weakref import WeakKeyDictionary

from PyQt5.QtCore import Qt, QObject, QAbstractItemModel, QModelIndex, \
                         QSortFilterProxyModel, QVariant, pyqtSignal as Signal,\
                         pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QImage, QPixmap, QPixmapCache, \
                        QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication

from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.capabilities.collection import BaseCollection
from weboob.capabilities.file import BaseFile
from weboob.capabilities.gallery import BaseGallery, BaseImage as GBaseImage
from weboob.capabilities.gauge import Gauge, GaugeSensor
from weboob.tools.compat import basestring
# TODO expand other cap objects when needed

from .qt import QtDo
from .thumbnails import try_get_thumbnail, store_thumbnail


__all__ = ['BackendListModel', 'ResultModel', 'FilterTypeModel']


class BackendListModel(QStandardItemModel):
    """Model for displaying a backends list with icons"""

    RoleBackendName = Qt.UserRole
    RoleCapability = Qt.UserRole + 1

    def __init__(self, weboob, *args, **kwargs):
        super(BackendListModel, self).__init__(*args, **kwargs)
        self.weboob = weboob

    def addBackends(self, cap=None, entry_all=True, entry_title=False):
        """
        Populate the model by adding backends.

        Appends backends to the model, without clearing previous entries.
        For each entry in the model, the cap name is stored under role
        RoleBackendName and the capability object under role
        RoleCapability.

        :param cap: capabilities to add (None to add all loaded caps)
        :param entry_all: if True, add a "All backends" entry
        :param entry_title: if True, add a disabled entry with the cap name
        """

        if entry_title:
            if cap:
                capname = cap.__name__
            else:
                capname = '(All capabilities)'

            item = QStandardItem(capname)
            item.setEnabled(False)
            self.appendRow(item)

        first = True
        for backend in self.weboob.iter_backends(caps=cap):
            if first and entry_all:
                item = QStandardItem('(All backends)')
                item.setData('', self.RoleBackendName)
                item.setData(cap, self.RoleCapability)
                self.appendRow(item)
            first = False

            item = QStandardItem(backend.name)
            item.setData(backend.name, self.RoleBackendName)
            item.setData(cap, self.RoleCapability)
            minfo = self.weboob.repositories.get_module_info(backend.NAME)
            icon_path = self.weboob.repositories.get_module_icon_path(minfo)
            if icon_path:
                pixmap = QPixmapCache.find(icon_path)
                if not pixmap:
                    pixmap = QPixmap(QImage(icon_path))
                item.setIcon(QIcon(pixmap))
            self.appendRow(item)


class DoWrapper(QtDo):
    """Wrapper for QtDo to use in DoQueue."""

    def __init__(self, *args, **kwargs):
        super(DoWrapper, self).__init__(*args, **kwargs)
        self.do_args = None

    def do(self, *args, **kwargs):
        self.do_args = (args, kwargs)

    def start(self):
        super(DoWrapper, self).do(*self.do_args[0], **self.do_args[1])
        self.do_args = None


class DoQueue(QObject):
    """Queue to limit the number of parallel Do processes."""

    def __init__(self):
        super(DoQueue, self).__init__()
        self.max_tasks = 10
        self.running = set()
        self.queue = deque()

    def add(self, doer):
        doer.finished.connect(self._finished)

        if len(self.running) < self.max_tasks:
            self.running.add(doer)
            doer.start()
        else:
            self.queue.append(doer)

    @Slot()
    def _finished(self):
        try:
            self.running.remove(self.sender())
        except KeyError:
            return

        try:
            doer = self.queue.popleft()
        except IndexError:
            return
        self.running.add(doer)
        doer.start()

    def stop(self):
        doers = list(self.running) + list(self.queue)
        self.running, self.queue = set(), deque()
        for do in doers:
            do.stop()


class Item(object):
    def __init__(self, obj, parent):
        self.obj = obj
        self.parent = parent
        self.children = None


class ResultModel(QAbstractItemModel):
    """Model for displaying objects and collections"""

    RoleObject = Qt.UserRole
    RoleCapability = Qt.UserRole + 1
    RoleBackendName = Qt.UserRole + 2

    jobAdded = Signal()
    jobFinished = Signal()

    def __init__(self, weboob, *args, **kwargs):
        super(ResultModel, self).__init__(*args, **kwargs)
        self.weboob = weboob
        self.resource_classes = []
        self.root = Item(None, None)
        self.columns = []

        self.limit = None

        self.jobs = DoQueue()
        self.jobExpanders = WeakKeyDictionary()
        self.jobFillers = WeakKeyDictionary()

    def __del__(self):
        try:
            self.jobs.stop()
        except:
            pass

    # configuration/general operation
    def setLimit(self, limit):
        self.limit = limit

    def clear(self):
        """Empty the model completely"""
        self.jobs.stop()
        #n = len(self.children.get(None, []))
        self.beginResetModel()
        #if n:
        #    self.beginRemoveRows(QModelIndex(), 0, max(0, n - 1))
        self.root = Item(None, None)
        self.endResetModel()
        #if n:
        #    self.endRemoveRows()

    @Slot(object)
    def _gotRootDone(self, obj):
        self._addToRoot(obj)

    def addRootDo(self, *args, **kwargs):
        """Make a weboob.do and add returned items to root of model"""
        process = DoWrapper(self.weboob, None)
        process.gotResponse.connect(self._gotRootDone)
        process.finished.connect(self.jobFinished)

        process.do(*args, **kwargs)
        self.jobAdded.emit()
        self.jobs.add(process)

    def addRootDoLimit(self, cls, *args, **kwargs):
        app = QApplication.instance()
        if cls is None:
            fields = None
        else:
            fields = self._expandableFields(cls)
        return self.addRootDo(app._do_complete, self.limit, fields, *args, **kwargs)

    def addRootItems(self, objs):
        for obj in objs:
            self._addToRoot(obj)

    def setColumnFields(self, columns):
        self.columns = tuple(((c,) if isinstance(c, basestring) else c) for c in columns)

    def setResourceClasses(self, classes):
        """Set accepted object classes for CapCollection.iter_resources"""
        self.resource_classes = classes

    def removeItem(self, qidx):
        item = qidx.internalPointer()
        assert item
        # TODO recursive?
        parent_qidx = qidx.parent()
        parent_item = item.parent
        assert parent_item is parent_qidx.internalPointer()

        n = parent_item.children.index(item)

        self.beginRemoveRows(parent_qidx, n, n)
        del parent_item.children[n]
        item.parent = None
        self.endRemoveRows()

    # internal operation
    def _addToRoot(self, obj):
        self._addItem(obj, self.root, QModelIndex())

    def _addItem(self, obj, parent, parent_qidx):
        item = Item(obj, parent)

        if parent.children is None:
            parent.children = []
        children = parent.children
        n = len(children)
        self.beginInsertRows(parent_qidx, n, n)
        children.append(item)
        self.endInsertRows()

    @Slot(object)
    def _expanderGotResponse(self, obj):
        parent_obj, parent_item = self.jobExpanders[self.sender()]
        row = parent_item.parent.children.index(parent_item)
        parent_qidx = self.createIndex(row, 0, parent_item)
        self._addItem(obj, parent_item, parent_qidx)

    def _prepareExpanderJob(self, obj, qidx):
        item = qidx.internalPointer()

        process = DoWrapper(self.weboob, None)
        process.finished.connect(self.jobFinished)
        process.gotResponse.connect(self._expanderGotResponse)
        self.jobExpanders[process] = (obj, item)
        return process

    def _expandableFields(self, cls):
        fields = set()

        for col in self.columns:
            for f in col:
                if f == 'id' or f in cls._fields:
                    fields.add(f)
        if 'thumbnail' in cls._fields:
            fields.add('thumbnail')

        return list(fields)

    def expandGauge(self, gauge, qidx):
        app = QApplication.instance()
        fields = self._expandableFields(GaugeSensor)

        process = self._prepareExpanderJob(gauge, qidx)
        process.do(app._do_complete, self.limit, fields, 'iter_sensors', gauge.id, backends=[gauge.backend])
        self.jobAdded.emit()
        self.jobs.add(process)

    def expandGallery(self, gall, qidx):
        app = QApplication.instance()
        fields = self._expandableFields(GBaseImage)

        process = self._prepareExpanderJob(gall, qidx)
        process.do(app._do_complete, self.limit, fields, 'iter_gallery_images', gall, backends=[gall.backend])
        self.jobAdded.emit()
        self.jobs.add(process)

    def expandCollection(self, coll, qidx):
        app = QApplication.instance()
        if len(self.resource_classes) == 1:
            fields = self._expandableFields(self.resource_classes[0])
        else:
            fields = None
            # at this point, we don't know the class of each object
            # FIXME reimplement _do_complete obj to filter dynamically

        process = self._prepareExpanderJob(coll, qidx)
        process.do(app._do_complete, self.limit, fields, 'iter_resources', self.resource_classes, coll.split_path, backends=[coll.backend])
        self.jobAdded.emit()
        self.jobs.add(process)

    def expandObj(self, obj, qidx):
        if isinstance(obj, BaseCollection):
            self.expandCollection(obj, qidx)
        elif isinstance(obj, BaseGallery):
            self.expandGallery(obj, qidx)
        elif isinstance(obj, Gauge):
            self.expandGauge(obj, qidx)

    def _getBackend(self, qidx):
        while qidx.isValid():
            item = qidx.internalPointer()
            if item.obj.backend:
                return item.obj.backend
            qidx = qidx.parent()

    def fillObj(self, obj, fields, qidx):
        assert qidx.isValid()
        item = qidx.internalPointer()

        process = DoWrapper(self.weboob, None)
        self.jobFillers[process] = item
        process.gotResponse.connect(self._fillerGotResponse)
        process.finished.connect(self.jobFinished)

        process.do('fillobj', obj, fields, backends=qidx.data(self.RoleBackendName))
        self.jobAdded.emit()
        self.jobs.add(process)

    @Slot(object)
    def _fillerGotResponse(self, new_obj):
        item = self.jobFillers[self.sender()]
        if new_obj is not None:
            item.obj = new_obj

        row = item.parent.children.index(item)
        qidx = self.createIndex(row, 0, item) # FIXME col 0 ?
        self.dataChanged.emit(qidx, qidx)

    # Qt model methods
    def index(self, row, col, parent_qidx):
        parent = parent_qidx.internalPointer() or self.root
        children = parent.children or ()
        if row >= len(children) or col >= len(self.columns):
            return QModelIndex()
        return self.createIndex(row, col, children[row])

    def parent(self, qidx):
        item = qidx.internalPointer() or self.root
        parent = item.parent
        if parent is None or parent.parent is None:
            return QModelIndex()

        gparent = parent.parent
        row = gparent.children.index(parent)
        return self.createIndex(row, 0, parent)

    def flags(self, qidx):
        obj = qidx.internalPointer()
        if obj is None:
            return Qt.NoItemFlags
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def rowCount(self, qidx):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        item = qidx.internalPointer() or self.root
        return len(item.children or ())

    def columnCount(self, qidx):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        return len(self.columns)

    def data(self, qidx, role):
        item = qidx.internalPointer()
        if item is None or item.obj is None:
            return QVariant()

        obj = item.obj

        if role == self.RoleBackendName:
            return QVariant(self._getBackend(qidx))
        elif role == self.RoleObject:
            return QVariant(obj)
        elif role == Qt.DecorationRole:
            return self._dataIcon(obj, qidx)
        elif role == Qt.DisplayRole:
            return self._dataText(obj, qidx)
        return QVariant()

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return QVariant()
        elif section >= len(self.columns):
            return QVariant()
        return '/'.join(self.columns[section])

    def hasChildren(self, qidx):
        item = qidx.internalPointer() or self.root

        obj = item.obj

        if isinstance(obj, BaseFile):
            return False
        # assume there are children, so a view may ask fetching
        children = item.children or [True]
        return bool(len(children))

    def canFetchMore(self, qidx):
        item = qidx.internalPointer()
        if item is None:
            return False
        return item.children is None

    def fetchMore(self, qidx):
        if not self.canFetchMore(qidx):
            return

        item = qidx.internalPointer()
        if item.children is None:
            item.children = []
        self.expandObj(item.obj, qidx)

    # overridable
    def _dataText(self, obj, qidx):
        fields = self.columns[qidx.column()]
        for field in fields:
            if hasattr(obj, field):
                data = getattr(obj, field)
                if data:
                    return QVariant(data)
        return QVariant()

    def _dataIcon(self, obj, qidx):
        if qidx.column() != 0:
            return QVariant()

        var = try_get_thumbnail(obj)
        if var:
            return var

        try:
            thumbnail = obj.thumbnail
        except AttributeError:
            return QVariant()
        if thumbnail is NotLoaded:
            self.fillObj(obj, ['thumbnail'], qidx)
        elif thumbnail is NotAvailable:
            return QVariant()
        elif thumbnail.data is NotLoaded:
            self.fillObj(thumbnail, ['data'], qidx)
        elif thumbnail.data is NotAvailable:
            return QVariant()
        else:
            img = QImage.fromData(thumbnail.data)
            store_thumbnail(obj)
            return QVariant(QIcon(QPixmap(img)))

        return QVariant()


class FilterTypeModel(QSortFilterProxyModel):
    def __init__(self, *args):
        super(FilterTypeModel, self).__init__(*args)
        self.types = []

    def setAcceptedTypes(self, types):
        self.types = types

    def filterAcceptsRow(self, row, parent_qidx):
        default = super(FilterTypeModel, self).filterAcceptsRow(row, parent_qidx)
        if not default:
            return False

        mdl = self.sourceModel()
        qidx = mdl.index(row, 0, parent_qidx)
        obj = mdl.data(qidx, ResultModel.RoleObject).value()
        actual = type(obj)
        for accepted in self.types:
            if issubclass(actual, accepted):
                return True
        return False

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2016  weboob project
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
# TODO expand other cap objects when needed

from .qt import QtDo


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


class ByIdDict(dict):
    """dict keeping objects by their `id()`

    This is used to store BaseObjects as key, because they are unhashable and
    so can't be put in a regular dict else.
    """

    def __init__(self):
        super(ByIdDict, self).__init__()
        self.objs = {}

    def __getitem__(self, k):
        return super(ByIdDict, self).__getitem__(id(k))

    def get(self, k, default=None):
        return super(ByIdDict, self).get(id(k), default)

    def __contains__(self, k):
        return super(ByIdDict, self).__contains__(id(k))

    def __setitem__(self, k, v):
        super(ByIdDict, self).__setitem__(id(k), v)
        self.objs[id(k)] = k

    def setdefault(self, k, v):
        self.objs[id(k)] = k
        return super(ByIdDict, self).setdefault(id(k), v)

    def __delitem__(self, k):
        super(ByIdDict, self).__delitem__(id(k))
        del self.objs[id(k)]

    def pop(self, k, *args, **kwargs):
        self.objs.pop(id(k), None)
        return super(ByIdDict, self).pop(id(k), *args, **kwargs)

    def clear(self):
        super(ByIdDict, self).clear()
        self.objs.clear()


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
        self.children = ByIdDict()
        self.parents = ByIdDict()
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
        self.children.clear()
        self.parents.clear()
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
        self.columns = columns

    def setResourceClasses(self, classes):
        """Set accepted object classes for CapCollection.iter_resources"""
        self.resource_classes = classes

    def removeItem(self, qidx):
        obj = qidx.internalPointer()
        assert obj
        # TODO recursive?
        parent_qidx = qidx.parent()
        parent_obj = parent_qidx.internalPointer()

        n = self.children[parent_obj].index(obj)

        self.beginRemoveRows(parent_qidx, n, n)
        self.parents.pop(obj, None)
        self.children.pop(obj, None)
        del self.children[parent_obj][n]
        self.endRemoveRows()

    # internal operation
    def _addToRoot(self, obj):
        self._addItem(obj, None, QModelIndex())

    def _addItem(self, obj, parent, parent_qidx):
        children = self.children.setdefault(parent, [])
        n = len(children)
        self.beginInsertRows(parent_qidx, n, n)
        children.append(obj)
        self.parents[obj] = parent
        self.endInsertRows()

    @Slot(object)
    def _expanderGotResponse(self, obj):
        parent, parent_qidx = self.jobExpanders[self.sender()]
        self._addItem(obj, parent, parent_qidx)

    def _prepareExpanderJob(self, parent, parent_qidx):
        process = DoWrapper(self.weboob, None)
        process.finished.connect(self.jobFinished)
        process.gotResponse.connect(self._expanderGotResponse)
        self.jobExpanders[process] = (parent, parent_qidx)
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
            obj = qidx.internalPointer()
            if obj.backend:
                return obj.backend
            qidx = qidx.parent()

    def fillObj(self, obj, fields, qidx):
        process = DoWrapper(self.weboob, None)
        self.jobFillers[process] = qidx
        process.gotResponse.connect(self._fillerGotResponse)
        process.finished.connect(self.jobFinished)

        process.do('fillobj', obj, fields, backends=qidx.data(self.RoleBackendName))
        self.jobAdded.emit()
        self.jobs.add(process)

    @Slot(object)
    def _fillerGotResponse(self, _):
        qidx = self.jobFillers[self.sender()]
        self.dataChanged.emit(qidx, qidx)

    # Qt model methods
    def index(self, row, col, parent_qidx):
        parent = parent_qidx.internalPointer()
        children = self.children.get(parent, ())
        if row >= len(children):
            return QModelIndex()
        return self.createIndex(row, col, children[row])

    def parent(self, qidx):
        obj = qidx.internalPointer()
        if obj is None:
            return QModelIndex()

        parent = self.parents.get(obj)
        if parent is None:
            return QModelIndex()

        gparent = self.parents[parent]
        row = self.children[gparent].index(parent)
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
        obj = qidx.internalPointer()
        return len(self.children.get(obj, []))

    def columnCount(self, qidx):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        return len(self.columns)

    def data(self, qidx, role):
        obj = qidx.internalPointer()
        if obj is None:
            return QVariant()

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
        obj = qidx.internalPointer()

        if isinstance(obj, BaseFile):
            return False
        # assume there are children, so a view may ask fetching
        children = self.children.get(obj, [True])
        return bool(len(children))

    def canFetchMore(self, qidx):
        obj = qidx.internalPointer()
        if obj is None:
            return False
        return obj not in self.children

    def fetchMore(self, qidx):
        if not self.canFetchMore(qidx):
            return

        obj = qidx.internalPointer()
        if obj is not None:
            self.children.setdefault(obj, [])
            self.expandObj(obj, qidx)

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
            return QVariant(QIcon(QPixmap(QImage.fromData(thumbnail.data))))
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

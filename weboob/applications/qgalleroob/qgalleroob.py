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

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty # python2

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from weboob.capabilities.gallery import CapGallery
from weboob.capabilities.image import CapImage
from weboob.tools.application.qt5 import QtApplication
from weboob.tools.application.qt5.thumbnails import try_get_thumbnail, store_thumbnail
from weboob.tools.config.yamlconfig import YamlConfig

from .main_window import MainWindow
from .bookmarks import BookmarkStorage


STOP_JOB = 'q'
RESUME_JOB = 'r'
FILL_JOB = 'f'


class QGalleroob(QtApplication):
    APPNAME = 'qgalleroob'
    VERSION = '1.5'
    COPYRIGHT = u'Copyright(C) 2016 Vincent A'
    DESCRIPTION = "Qt application to view image galleries."
    SHORT_DESCRIPTION = "search for images"
    #~ CONFIG = {'queries': {}}
    STORAGE = {'bookmarks': [], 'ignored': []}

    def __init__(self, *args, **kwargs):
        super(QGalleroob, self).__init__(*args, **kwargs)
        self.demands = Queue()
        self.on_demand = False

    def deinit(self):
        self.fetchStop()
        super(QGalleroob, self).deinit()

    def main(self, argv):
        self.load_backends(CapGallery)
        self.load_backends(CapImage)
        self.create_storage()
        self.load_config(klass=YamlConfig)

        self.bookmarks = BookmarkStorage(self.storage)

        main_window = MainWindow(self.config, self.storage, self.weboob)
        main_window.show()
        return self.weboob.loop()

    def prepareJob(self, on_demand):
        self.fetchStop()
        self.demands = Queue()
        self.on_demand = on_demand

    @Slot()
    def fetchStop(self):
        self.demands.put((STOP_JOB,))

    @Slot()
    def fetchMore(self):
        self.demands.put((RESUME_JOB,))

    def fetchFill(self, t):
        self.demands.put((FILL_JOB,) + t)

    dataChanged = Signal(int)

    def _do_complete_obj(self, backend, fields, obj):
        has_thumbnail = try_get_thumbnail(obj)
        if has_thumbnail:
            fields = fields - {'thumbnail'}

        obj = super(QGalleroob, self)._do_complete_obj(backend, fields, obj)

        if has_thumbnail:
            return obj

        if getattr(obj, 'thumbnail', None) and not obj.thumbnail.data:
            obj.thumbnail = super(QGalleroob, self)._do_complete_obj(backend, None, obj.thumbnail)
            store_thumbnail(obj)
        return obj

    def _do_complete_iter(self, backend, count, fields, res):
        q = self.demands
        pagin = self.on_demand
        limit = count
        more = 0

        def do_fillobj(t):
            _, fobj, ffields, cookie = t
            backend.fillobj(fobj, ffields)
            self.dataChanged.emit(cookie)

        i = 0
        for obj in res:
            if not obj.backend:
                obj.backend = backend.name

            if self.bookmarks.is_ignored(obj.fullid):
                continue

            fields = set(obj._fields)
            fields.discard('data')
            obj = self._do_complete_obj(backend, fields, obj)
            if getattr(obj, 'thumbnail', None) and not obj.thumbnail.data and not try_get_thumbnail(obj):
                obj.thumbnail = self._do_complete_obj(backend, None, obj.thumbnail)
            yield obj

            while True:
                try:
                    t = q.get(False)
                except Empty:
                    break
                else:
                    if t[0] == STOP_JOB:
                        return
                    elif t[0] == RESUME_JOB:
                        more += 1
                    else:
                        do_fillobj(t)
                    del t

            i += 1

            if pagin:
                if not (i % count):
                    if more > 0:
                        more -= 1
                    else:
                        while True:
                            t = q.get()
                            if t[0] == STOP_JOB:
                                return
                            elif t[0] == RESUME_JOB:
                                break
                            elif t[0] == FILL_JOB:
                                do_fillobj(t)
                            del t
            elif i >= limit:
                return

        #self.endHit.emit()


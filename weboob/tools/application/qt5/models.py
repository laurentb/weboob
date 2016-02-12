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


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QImage, QPixmap, QPixmapCache, \
                        QStandardItemModel, QStandardItem


__all__ = ['BackendListModel']


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
                item.setData('', Qt.UserRole)
                item.setData(cap, Qt.UserRole + 1)
                self.appendRow(item)
            first = False

            item = QStandardItem(backend.name)
            item.setData(backend.name, Qt.UserRole)
            item.setData(cap, Qt.UserRole + 1)
            minfo = self.weboob.repositories.get_module_info(backend.name)
            icon_path = self.weboob.repositories.get_module_icon_path(minfo)
            if icon_path:
                pixmap = QPixmapCache.find(icon_path)
                if not pixmap:
                    pixmap = QPixmap(QImage(icon_path))
                item.setIcon(QIcon(pixmap))
            self.appendRow(item)

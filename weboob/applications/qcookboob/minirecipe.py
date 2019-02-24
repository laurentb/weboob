# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

import requests

from PyQt5.QtGui import QIcon, QImage, QPixmap, QPixmapCache
from PyQt5.QtWidgets import QFrame, QApplication
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.applications.qcookboob.ui.minirecipe_ui import Ui_MiniRecipe
from weboob.capabilities.base import empty


class MiniRecipe(QFrame):
    def __init__(self, weboob, backend, recipe, parent=None):
        super(MiniRecipe, self).__init__(parent)
        self.parent = parent
        self.ui = Ui_MiniRecipe()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.recipe = recipe
        self.ui.titleLabel.setText(recipe.title)
        if not empty(recipe.short_description):
            if len(recipe.short_description) > 300:
                self.ui.shortDescLabel.setText('%s [...]'%recipe.short_description[:300])
            else:
                self.ui.shortDescLabel.setText(recipe.short_description)
        else:
            self.ui.shortDescLabel.setText('')
        self.ui.backendButton.setText(backend.name)
        minfo = self.weboob.repositories.get_module_info(backend.NAME)
        icon_path = self.weboob.repositories.get_module_icon_path(minfo)
        if icon_path:
            pixmap = QPixmapCache.find(icon_path)
            if not pixmap:
                pixmap = QPixmap(QImage(icon_path))
            self.ui.backendButton.setIcon(QIcon(pixmap))

        self.ui.newTabButton.clicked.connect(self.newTabPressed)
        self.ui.viewButton.clicked.connect(self.viewPressed)
        self.ui.viewThumbnailButton.clicked.connect(self.gotThumbnail)

        if self.parent.parent.ui.showTCheck.isChecked():
            self.gotThumbnail()

    @Slot()
    def gotThumbnail(self):
        try:
            url = self.recipe.picture.thumbnail.url
        except AttributeError:
            return

        if not empty(url):
            data = requests.get(url).content
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img).scaledToHeight(100,Qt.SmoothTransformation))

    @Slot()
    def viewPressed(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        recipe = self.backend.get_recipe(self.recipe.id)
        if recipe:
            self.parent.doAction('Recipe "%s"' %
                                 recipe.title, self.parent.displayRecipe, [recipe, self.backend])

    @Slot()
    def newTabPressed(self):
        recipe = self.backend.get_recipe(self.recipe.id)
        self.parent.parent.newTab(u'Recipe "%s"' %
             recipe.title, self.backend, recipe=recipe)

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        if event.button() == 2:
            self.gotThumbnail()
        elif event.button() == 4:
            self.newTabPressed()
        else:
            self.viewPressed()

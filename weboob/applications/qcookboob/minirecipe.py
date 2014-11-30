# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

import urllib

from PyQt4.QtGui import QFrame, QImage, QPixmap, QApplication
from PyQt4.QtCore import Qt, SIGNAL

from weboob.applications.qcookboob.ui.minirecipe_ui import Ui_MiniRecipe
from weboob.capabilities.base import empty


class MiniRecipe(QFrame):
    def __init__(self, weboob, backend, recipe, parent=None):
        QFrame.__init__(self, parent)
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
        self.ui.backendLabel.setText(backend.name)

        self.connect(self.ui.newTabButton, SIGNAL("clicked()"), self.newTabPressed)
        self.connect(self.ui.viewButton, SIGNAL("clicked()"), self.viewPressed)
        self.connect(self.ui.viewThumbnailButton, SIGNAL("clicked()"), self.gotThumbnail)

        if self.parent.parent.ui.showTCheck.isChecked():
            self.gotThumbnail()

    def gotThumbnail(self):
        if not empty(self.recipe.thumbnail_url):
            data = urllib.urlopen(self.recipe.thumbnail_url).read()
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img).scaledToHeight(100,Qt.SmoothTransformation))

    def viewPressed(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        recipe = self.backend.get_recipe(self.recipe.id)
        if recipe:
            self.parent.doAction('Details of recipe "%s"' %
                                 recipe.title, self.parent.displayRecipe, [recipe, self.backend])

    def newTabPressed(self):
        recipe = self.backend.get_recipe(self.recipe.id)
        self.parent.parent.newTab(u'Details of recipe "%s"' %
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

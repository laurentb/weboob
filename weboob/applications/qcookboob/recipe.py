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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QFrame, QImage, QPixmap

from weboob.applications.qcookboob.ui.recipe_ui import Ui_Recipe
from weboob.capabilities.base import empty


class Recipe(QFrame):
    def __init__(self, recipe, backend, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_Recipe()
        self.ui.setupUi(self)

        self.recipe = recipe
        self.backend = backend
        self.gotThumbnail()

        self.ui.idEdit.setText(u'%s@%s' % (recipe.id, backend.name))
        if not empty(recipe.title):
            self.ui.titleLabel.setText(recipe.title)
        if not empty(recipe.nb_person):
            self.ui.nbPersonLabel.setText('%s'%recipe.nb_person)
        else:
            self.ui.nbPersonLabel.parent().hide()
        if not empty(recipe.preparation_time):
            self.ui.prepTimeLabel.setText('%s min' % recipe.preparation_time)
        else:
            self.ui.prepTimeLabel.parent().hide()
        if not empty(recipe.cooking_time):
            self.ui.cookingTimeLabel.setText('%s min' % recipe.cooking_time)
        else:
            self.ui.cookingTimeLabel.parent().hide()
        if not empty(recipe.ingredients):
            txt = u''
            for ing in recipe.ingredients:
                txt += '* %s\n' % ing
            self.ui.ingredientsPlain.setPlainText('%s' % txt)
        else:
            self.ui.ingredientsPlain.parent().hide()
        if not empty(recipe.instructions):
            self.ui.instructionsPlain.setPlainText('%s' % recipe.instructions)
        else:
            self.ui.instructionsPlain.parent().hide()
        if not empty(recipe.comments):
            txt = u''
            for com in recipe.comments:
                txt += '* %s\n' % com
            self.ui.commentsPlain.setPlainText('%s' % txt)
        else:
            self.ui.commentsPlain.parent().hide()

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)
        self.ui.verticalLayout_2.setAlignment(Qt.AlignTop)

    def gotThumbnail(self):
        if not empty(self.recipe.picture_url):
            data = urllib.urlopen(self.recipe.picture_url).read()
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img).scaledToWidth(250,Qt.SmoothTransformation))

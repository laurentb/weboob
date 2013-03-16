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

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QFrame, QImage, QPixmap

from weboob.applications.qcookboob.ui.recipe_ui import Ui_Recipe
from weboob.capabilities.base import empty


class Recipe(QFrame):
    def __init__(self, recipe, backend, parent=None):
        QFrame.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_Recipe()
        self.ui.setupUi(self)
        langs = LANGUAGE_CONV.keys()
        langs.sort()
        for lang in langs:
            self.ui.langCombo.addItem(lang)

        self.recipe = recipe
        self.backend = backend
        self.ui.titleLabel.setText(recipe.original_title)
        self.ui.durationLabel.setText(unicode(recipe.duration))
        self.gotThumbnail()

        self.ui.idEdit.setText(u'%s@%s' % (recipe.id, backend.name))
        if not empty(recipe.other_titles):
            self.ui.otherTitlesPlain.setPlainText('\n'.join(recipe.other_titles))
        else:
            self.ui.otherTitlesPlain.parent().hide()
        if not empty(recipe.release_date):
            self.ui.releaseDateLabel.setText(recipe.release_date.strftime('%Y-%m-%d'))
        else:
            self.ui.releaseDateLabel.parent().hide()
        if not empty(recipe.duration):
            self.ui.durationLabel.setText('%s min' % recipe.duration)
        else:
            self.ui.durationLabel.parent().hide()
        if not empty(recipe.pitch):
            self.ui.pitchPlain.setPlainText('%s' % recipe.pitch)
        else:
            self.ui.pitchPlain.parent().hide()
        if not empty(recipe.country):
            self.ui.countryLabel.setText('%s' % recipe.country)
        else:
            self.ui.countryLabel.parent().hide()
        if not empty(recipe.note):
            self.ui.noteLabel.setText('%s' % recipe.note)
        else:
            self.ui.noteLabel.parent().hide()
        for role in ROLE_LIST:
            self.ui.castingCombo.addItem('%ss' % role)

        self.ui.verticalLayout.setAlignment(Qt.AlignTop)
        self.ui.verticalLayout_2.setAlignment(Qt.AlignTop)

    def gotThumbnail(self):
        if not empty(self.recipe.thumbnail_url):
            data = urllib.urlopen(self.recipe.thumbnail_url).read()
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

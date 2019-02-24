# -*- coding: utf-8 -*-

# Copyright(C) 2016  weboob project
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

import codecs
import os

from PyQt5.QtWidgets import QCompleter
from PyQt5.QtCore import QStringListModel


__all__ = ['HistoryCompleter']


class HistoryCompleter(QCompleter):
    def __init__(self, hist_path, *args, **kwargs):
        super(HistoryCompleter, self).__init__(*args, **kwargs)
        self.setModel(QStringListModel())
        self.max_history = 50
        self.search_history = []
        self.hist_path = hist_path

    def addString(self, s):
        if not s:
            return
        if len(self.search_history) > self.max_history:
            self.search_history.pop(0)
        if s not in self.search_history:
            self.search_history.append(s)
            self.updateCompletion()

    def updateCompletion(self):
        self.model().setStringList(self.search_history)

    def load(self):
        """ Return search string history list loaded from history file """
        self.search_history = []
        if os.path.exists(self.hist_path):
            with codecs.open(self.hist_path, 'r', 'utf-8') as f:
                conf_hist = f.read().strip()
            if conf_hist:
                self.search_history = conf_hist.split('\n')
        self.updateCompletion()

    def save(self):
        """ Save search history in history file. """
        if len(self.search_history) > 0:
            with codecs.open(self.hist_path, 'w', 'utf-8') as f:
                f.write('\n'.join(self.search_history))

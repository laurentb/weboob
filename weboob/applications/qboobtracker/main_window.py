# -*- coding: utf-8 -*-

# Copyright(C) 2013 Sébastien Monel
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

from __future__ import unicode_literals

from PyQt5.QtWidgets import QMessageBox, QInputDialog
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.tools.application.qt5 import QtMainWindow
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.tools.application.qt5.search_history import HistoryCompleter
from weboob.tools.application.qt5.models import ResultModel
from weboob.capabilities.bugtracker import CapBugTracker, Query, Change, Update

from .ui.main_window_ui import Ui_MainWindow

import os
import re
import shlex


KEYWORDS = ['project', 'backend', 'category', 'title', 'author', 'assignee', 'status', 'tags']
KWD_MATCH = re.compile(r'^(%s):(.*)$' % '|'.join(KEYWORDS))


def string_to_queries(s):
    # TODO rewrite all when there are finer criteria
    # and when more complex expressions can be written

    tokens = shlex.split(s)  # raises ValueError

    criteria = {}

    for tok in tokens:
        m = KWD_MATCH.match(tok)
        if not m:
            raise ValueError('%r is not a valid criterion' % tok)

        k, v = m.groups()
        criteria.setdefault(k, []).append(v)

    queries = [Query()]
    for k, values in criteria.items():
        if k == 'tags':
            values = [tuple(val.split(',')) for val in values]

        if len(values) == 1:
            v, = values
            for q in queries:
                setattr(q, k, v)
        else:
            dupq = {}
            for v in values:
                dupq[v] = []
                for q in queries:
                    q = q.copy()
                    setattr(q, k, v)
                    dupq[v].append(q)

            queries = sum(dupq.values(), [])

    return queries


class MainWindow(QtMainWindow):
    def __init__(self, config, storage, weboob, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.storage = storage
        self.weboob = weboob
        self.process = None

        # search history is a list of patterns which have been searched
        history_path = os.path.join(self.weboob.workdir, 'qboobtracker_history')
        qc = HistoryCompleter(history_path, self)
        qc.load()
        qc.setCaseSensitivity(Qt.CaseInsensitive)
        self.ui.searchEdit.setCompleter(qc)

        self.ui.actionBackends.triggered.connect(self.backendsConfig)

        self.ui.searchEdit.returnPressed.connect(self.doSearch)
        self.ui.searchButton.clicked.connect(self.doSearch)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

        self.mdl = ResultModel(self.weboob)
        self.mdl.setColumnFields(['id', 'title', 'status', 'creation', 'author', 'updated', 'assignee', 'tags'])

        self.ui.bugList.setModel(self.mdl)
        self.ui.bugList.addAction(self.ui.actionBulk)
        self.ui.actionBulk.triggered.connect(self.doBulk)

    @Slot()
    def doBulk(self):
        qidxes = self.ui.bugList.selectionModel().selectedIndexes()
        cols = set(qidx.column() for qidx in qidxes)
        if len(cols) != 1:
            return

        col, = cols
        colname = self.mdl.headerData(col, Qt.Horizontal, Qt.DisplayRole)
        if colname not in ('status', 'assignee'):
            return

        objs = [qidx.data(ResultModel.RoleObject) for qidx in qidxes]
        project = objs[0].project
        if colname == 'status':
            vals = [status.name for status in project.statuses or []]
            val, ok = QInputDialog.getItem(self, self.tr('Bulk edit'), self.tr('Select new status for selected items'), vals, 0, False)
        elif colname == 'assignee':
            vals = [user.name for user in project.members or []]
            val, ok = QInputDialog.getItem(self, self.tr('Bulk edit'), self.tr('Select new assignee for selected items'), vals, 0, False)
        if not ok:
            return

        for obj in objs:
            change = Change()
            change.field = colname
            change.new = val

            update = Update()
            update.changes = [change]

            self.weboob.do('update_issue', obj, update, backends=(obj.backend,))

    @Slot()
    def doSearch(self):
        pattern = self.ui.searchEdit.text()

        try:
            queries = string_to_queries(pattern)
        except ValueError as e:
            QMessageBox.critical(self, self.tr('Error in search query'), str(e))
            return

        self.ui.searchEdit.completer().addString(pattern)

        self.mdl.clear()
        self.process = self.mdl.addRootDo(self.do_search, queries)

    def do_search(self, backend, queries):
        for q in queries:
            if q.backend and q.backend != backend.name:
                continue
            for issue in backend.iter_issues(q):
                yield issue

    def closeEvent(self, event):
        self.ui.searchEdit.completer().save()
        super(MainWindow, self).closeEvent(event)

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapBugTracker,), self)
        if bckndcfg.run():
            pass

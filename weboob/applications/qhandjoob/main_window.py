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

from PyQt4.QtGui import QListWidgetItem, QApplication, QCompleter
from PyQt4.QtCore import SIGNAL, Qt, QStringList

from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.job import CapJob

from .ui.main_window_ui import Ui_MainWindow

import os
import codecs


class JobListWidgetItem(QListWidgetItem):
    def __init__(self, job, *args, **kwargs):
        QListWidgetItem.__init__(self, *args, **kwargs)
        self.job = job

    def __lt__(self, other):
        if self.job.publication_date and other.job.publication_date:
            return self.job.publication_date < other.job.publication_date
        else:
            return False

    def setAttrs(self, storage):
        text = u'%s - %s' % (self.job.backend, self.job.title)
        self.setText(text)


class MainWindow(QtMainWindow):
    def __init__(self, config, storage, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.storage = storage
        self.weboob = weboob
        self.process = None
        self.displayed_photo_idx = 0
        self.process_photo = {}
        self.process_bookmarks = {}

        # search history is a list of patterns which have been searched
        self.search_history = self.loadSearchHistory()
        self.updateCompletion()

        self.ui.jobFrame.hide()

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)

        self.connect(self.ui.searchEdit, SIGNAL('returnPressed()'), self.doSearch)
        self.connect(self.ui.jobList, SIGNAL('currentItemChanged(QListWidgetItem*, QListWidgetItem*)'), self.jobSelected)
        self.connect(self.ui.searchButton, SIGNAL('clicked()'), self.doSearch)

        self.connect(self.ui.refreshButton, SIGNAL('clicked()'), self.doAdvancedSearch)
        self.connect(self.ui.queriesTabWidget, SIGNAL('currentChanged(int)'), self.tabChange)
        self.connect(self.ui.jobListAdvancedSearch, SIGNAL('currentItemChanged(QListWidgetItem*, QListWidgetItem*)'), self.jobSelected)

        self.connect(self.ui.idEdit, SIGNAL('returnPressed()'), self.openJob)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

    def loadSearchHistory(self):
        ''' Return search string history list loaded from history file
        '''
        result = []
        history_path = os.path.join(self.weboob.workdir, 'qhandjoob_history')
        if os.path.exists(history_path):
            f = codecs.open(history_path, 'r', 'utf-8')
            conf_hist = f.read()
            f.close()
            if conf_hist is not None and conf_hist.strip() != '':
                result = conf_hist.strip().split('\n')
        return result

    def saveSearchHistory(self):
        ''' Save search history in history file
        '''
        if len(self.search_history) > 0:
            history_path = os.path.join(self.weboob.workdir, 'qhandjoob_history')
            f = codecs.open(history_path, 'w', 'utf-8')
            f.write('\n'.join(self.search_history))
            f.close()

    def updateCompletion(self):
        qc = QCompleter(QStringList(self.search_history), self)
        qc.setCaseSensitivity(Qt.CaseInsensitive)
        self.ui.searchEdit.setCompleter(qc)

    def tabChange(self, index):
        if index == 1:
            self.doAdvancedSearch()

    def searchFinished(self):
        self.process = None
        QApplication.restoreOverrideCursor()

    def doAdvancedSearch(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.jobListAdvancedSearch.clear()

        self.process = QtDo(self.weboob, self.addJobAdvancedSearch, fb=self.searchFinished)
        self.process.do('advanced_search_job')

    def doSearch(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        pattern = unicode(self.ui.searchEdit.text())

        # arbitrary max number of completion word
        if pattern:
            if len(self.search_history) > 50:
                self.search_history.pop(0)
            if pattern not in self.search_history:
                self.search_history.append(pattern)
                self.updateCompletion()

        self.ui.jobList.clear()
        self.process = QtDo(self.weboob, self.addJobSearch, fb=self.searchFinished)
        self.process.do('search_job', pattern)

    def addJobSearch(self, job):
        item = self.addJob(job)
        if item:
            self.ui.jobList.addItem(item)

    def addJobAdvancedSearch(self, job):
        item = self.addJob(job)
        if item:
            self.ui.jobListAdvancedSearch.addItem(item)

    def addJob(self, job):
        if not job:
            return

        item = JobListWidgetItem(job)
        item.setAttrs(self.storage)
        return item

    def closeEvent(self, event):
        self.saveSearchHistory()
        QtMainWindow.closeEvent(self, event)

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapJob,), self)
        if bckndcfg.run():
            pass

    def jobSelected(self, item, prev):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if item is not None:
            job = item.job
            self.ui.queriesTabWidget.setEnabled(False)

            self.process = QtDo(self.weboob, self.gotJob)
            self.process.do('fillobj', job, backends=job.backend)

        else:
            job = None

        self.setJob(job)

        if prev:
            prev.setAttrs(self.storage)

    def openJob(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        url = unicode(self.ui.idEdit.text())
        if not url:
            return

        for backend in self.weboob.iter_backends():
            job = backend.get_job_advert(url)
            if job:
                self.process = QtDo(self.weboob, self.gotJob)
                self.process.do('fillobj', job, backends=job.backend)
                break

        self.setJob(job)
        self.ui.idEdit.clear()
        QApplication.restoreOverrideCursor()

    def gotJob(self, job):
        self.setJob(job)
        self.ui.queriesTabWidget.setEnabled(True)
        self.process = None

    def setJob(self, job):
        if job:
            self.ui.descriptionEdit.setText("%s" % job.description)
            self.ui.titleLabel.setText("<h1>%s</h1>" % job.title)
            self.ui.idLabel.setText("%s" % job.id)
            self.ui.jobNameLabel.setText("%s" % job.job_name)
            self.ui.publicationDateLabel.setText("%s" % job.publication_date)
            self.ui.societyNameLabel.setText("%s" % job.society_name)
            self.ui.placeLabel.setText("%s" % job.place)
            self.ui.payLabel.setText("%s" % job.pay)
            self.ui.contractTypeLabel.setText("%s" % job.contract_type)
            self.ui.formationLabel.setText("%s" % job.formation)
            self.ui.experienceLabel.setText("%s" % job.experience)
            self.ui.urlLabel.setText("<a href='%s'>%s</a>" % (job.url, job.url))
            self.ui.jobFrame.show()
        else:
            self.ui.jobFrame.hide()

        QApplication.restoreOverrideCursor()

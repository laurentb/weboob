# -*- coding: utf-8 -*-

# Copyright(C) 2013 Sébastien Monel
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

from PyQt5.QtWidgets import QListWidgetItem, QApplication
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.tools.application.qt5 import QtMainWindow, QtDo
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.tools.application.qt5.search_history import HistoryCompleter
from weboob.capabilities.job import CapJob

from .ui.main_window_ui import Ui_MainWindow

import os


class JobListWidgetItem(QListWidgetItem):
    def __init__(self, job, *args, **kwargs):
        super(JobListWidgetItem, self).__init__(*args, **kwargs)
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
        super(MainWindow, self).__init__(parent)
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
        history_path = os.path.join(self.weboob.workdir, 'qhandjoob_history')
        qc = HistoryCompleter(history_path, self)
        qc.load()
        qc.setCaseSensitivity(Qt.CaseInsensitive)
        self.ui.searchEdit.setCompleter(qc)

        self.ui.jobFrame.hide()

        self.ui.actionBackends.triggered.connect(self.backendsConfig)

        self.ui.searchEdit.returnPressed.connect(self.doSearch)
        self.ui.jobList.currentItemChanged.connect(self.jobSelected)
        self.ui.searchButton.clicked.connect(self.doSearch)

        self.ui.refreshButton.clicked.connect(self.doAdvancedSearch)
        self.ui.queriesTabWidget.currentChanged.connect(self.tabChange)
        self.ui.jobListAdvancedSearch.currentItemChanged.connect(self.jobSelected)

        self.ui.idEdit.returnPressed.connect(self.openJob)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

    @Slot(int)
    def tabChange(self, index):
        if index == 1:
            self.doAdvancedSearch()

    def searchFinished(self):
        self.process = None
        QApplication.restoreOverrideCursor()

    @Slot()
    def doAdvancedSearch(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.jobListAdvancedSearch.clear()

        self.process = QtDo(self.weboob, self.addJobAdvancedSearch, fb=self.searchFinished)
        self.process.do('advanced_search_job')

    @Slot()
    def doSearch(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        pattern = self.ui.searchEdit.text()

        self.ui.searchEdit.completer().addString(pattern)

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
        self.ui.searchEdit.completer().save()
        QtMainWindow.closeEvent(self, event)

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapJob,), self)
        if bckndcfg.run():
            pass

    @Slot(QListWidgetItem, QListWidgetItem)
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

    @Slot()
    def openJob(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        url = self.ui.idEdit.text()
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

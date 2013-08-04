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

from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtCore import SIGNAL

from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.job import ICapJob

from .ui.main_window_ui import Ui_MainWindow


class JobListWidgetItem(QListWidgetItem):
    def __init__(self, job, *args, **kwargs):
        QListWidgetItem.__init__(self, *args, **kwargs)
        self.job = job

    def __lt__(self, other):
        return self.job.publication_date < other.job.publication_date

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

        self.ui.jobFrame.hide()

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)
        self.connect(self.ui.searchEdit, SIGNAL('returnPressed()'), self.doSearch)
        self.connect(self.ui.jobList, SIGNAL('currentItemChanged(QListWidgetItem*, QListWidgetItem*)'), self.jobSelected)
        self.connect(self.ui.searchButton, SIGNAL('clicked()'), self.doSearch)

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

    def doSearch(self):
        pattern = unicode(self.ui.searchEdit.text())
        self.ui.jobList.clear()
        self.process = QtDo(self.weboob, self.addJob)
        self.process.do('search_job', pattern)

    def addJob(self, backend, job):
        if not backend:
            self.process = None
            return

        if not job:
            return

        item = JobListWidgetItem(job)
        item.setAttrs(self.storage)
        self.ui.jobList.addItem(item)

    def closeEvent(self, event):
        QtMainWindow.closeEvent(self, event)

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (ICapJob,), self)
        if bckndcfg.run():
            pass

    def jobSelected(self, item, prev):
        if item is not None:
            job = item.job
            self.ui.queriesFrame.setEnabled(False)

            self.process = QtDo(self.weboob, self.gotJob)
            self.process.do('fillobj', job, backends=job.backend)

        else:
            job = None

        self.setJob(job)

        if prev:
            prev.setAttrs(self.storage)

    def gotJob(self, backend, job):
        if not backend:
            self.ui.queriesFrame.setEnabled(True)
            self.process = None
            return

        self.setJob(job)

    def setJob(self, job):
        if job:
            self.ui.descriptionEdit.setText("%s" % job.description)
            self.ui.titleLabel.setText("<h1>%s</h1>" % job.title)
            self.ui.backendLabel.setText("%s" % job.backend)
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

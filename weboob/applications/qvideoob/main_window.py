# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from PyQt4.QtCore import SIGNAL

from weboob.capabilities.video import CapVideo
from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg

from weboob.applications.qvideoob.ui.main_window_ui import Ui_MainWindow

from .video import Video
from .minivideo import MiniVideo


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, app, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.minivideos = []
        self.app = app

        self.ui.sortbyEdit.setCurrentIndex(int(self.config.get('settings', 'sortby')))
        self.ui.nsfwCheckBox.setChecked(int(self.config.get('settings', 'nsfw')))
        self.ui.sfwCheckBox.setChecked(int(self.config.get('settings', 'sfw')))

        self.connect(self.ui.searchEdit, SIGNAL("returnPressed()"), self.search)
        self.connect(self.ui.urlEdit, SIGNAL("returnPressed()"), self.openURL)
        self.connect(self.ui.nsfwCheckBox, SIGNAL("stateChanged(int)"), self.nsfwChanged)
        self.connect(self.ui.sfwCheckBox, SIGNAL("stateChanged(int)"), self.sfwChanged)

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)

        self.loadBackendsList()

        if self.ui.backendEdit.count() == 0:
            self.backendsConfig()

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapVideo,), self)
        if bckndcfg.run():
            self.loadBackendsList()

    def loadBackendsList(self):
        self.ui.backendEdit.clear()
        for i, backend in enumerate(self.weboob.iter_backends()):
            if i == 0:
                self.ui.backendEdit.addItem('All backends', '')
            self.ui.backendEdit.addItem(backend.name, backend.name)
            if backend.name == self.config.get('settings', 'backend'):
                self.ui.backendEdit.setCurrentIndex(i+1)

        if self.ui.backendEdit.count() == 0:
            self.ui.searchEdit.setEnabled(False)
            self.ui.urlEdit.setEnabled(False)
        else:
            self.ui.searchEdit.setEnabled(True)
            self.ui.urlEdit.setEnabled(True)

    def nsfwChanged(self, state):
        self.config.set('settings', 'nsfw', int(self.ui.nsfwCheckBox.isChecked()))
        self.updateVideosDisplay()

    def sfwChanged(self, state):
        self.config.set('settings', 'sfw', int(self.ui.sfwCheckBox.isChecked()))
        self.updateVideosDisplay()

    def updateVideosDisplay(self):
        for minivideo in self.minivideos:
            if (minivideo.video.nsfw and self.ui.nsfwCheckBox.isChecked() or
                    not minivideo.video.nsfw and self.ui.sfwCheckBox.isChecked()):
                minivideo.show()
            else:
                minivideo.hide()

    def search(self):
        pattern = unicode(self.ui.searchEdit.text())
        if not pattern:
            return

        for minivideo in self.minivideos:
            self.ui.scrollAreaContent.layout().removeWidget(minivideo)
            minivideo.hide()
            minivideo.deleteLater()

        self.minivideos = []
        self.ui.searchEdit.setEnabled(False)

        backend_name = str(self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()).toString())

        def finished():
            self.ui.searchEdit.setEnabled(True)
            self.process = None

        self.process = QtDo(self.weboob, self.addVideo, fb=finished)
        self.process.do(self.app._do_complete, 20, (), 'search_videos', pattern, self.ui.sortbyEdit.currentIndex(), nsfw=True, backends=backend_name)

    def addVideo(self, video):
        minivideo = MiniVideo(self.weboob, self.weboob[video.backend], video)
        self.ui.scrollAreaContent.layout().addWidget(minivideo)
        self.minivideos.append(minivideo)
        if (video.nsfw and not self.ui.nsfwCheckBox.isChecked() or
                not video.nsfw and not self.ui.sfwCheckBox.isChecked()):
            minivideo.hide()

    def openURL(self):
        url = unicode(self.ui.urlEdit.text())
        if not url:
            return

        for backend in self.weboob.iter_backends():
            video = backend.get_video(url)
            if video:
                video_widget = Video(video, self)
                video_widget.show()

        self.ui.urlEdit.clear()

    def closeEvent(self, ev):
        self.config.set('settings', 'backend', str(self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()).toString()))
        self.config.set('settings', 'sortby', self.ui.sortbyEdit.currentIndex())
        self.config.save()
        ev.accept()

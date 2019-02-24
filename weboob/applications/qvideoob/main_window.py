# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from PyQt5.QtCore import pyqtSlot as Slot

from weboob.capabilities.video import CapVideo
from weboob.tools.application.qt5 import QtMainWindow, QtDo
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.tools.application.qt5.models import BackendListModel

from weboob.applications.qvideoob.ui.main_window_ui import Ui_MainWindow

from .video import Video
from .minivideo import MiniVideo


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, app, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.minivideos = []
        self.app = app

        self.ui.sortbyEdit.setCurrentIndex(int(self.config.get('settings', 'sortby')))
        self.ui.nsfwCheckBox.setChecked(int(self.config.get('settings', 'nsfw')))
        self.ui.sfwCheckBox.setChecked(int(self.config.get('settings', 'sfw')))

        self.ui.searchEdit.returnPressed.connect(self.search)
        self.ui.urlEdit.returnPressed.connect(self.openURL)
        self.ui.nsfwCheckBox.stateChanged.connect(self.nsfwChanged)
        self.ui.sfwCheckBox.stateChanged.connect(self.sfwChanged)

        self.ui.actionBackends.triggered.connect(self.backendsConfig)

        self.loadBackendsList()

        if self.ui.backendEdit.count() == 0:
            self.backendsConfig()

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapVideo,), self)
        if bckndcfg.run():
            self.loadBackendsList()

    def loadBackendsList(self):
        model = BackendListModel(self.weboob)
        model.addBackends()
        self.ui.backendEdit.setModel(model)

        current_backend = self.config.get('settings', 'backend')
        idx = self.ui.backendEdit.findData(current_backend)
        if idx >= 0:
            self.ui.backendEdit.setCurrentIndex(idx)

        if self.ui.backendEdit.count() == 0:
            self.ui.searchEdit.setEnabled(False)
            self.ui.urlEdit.setEnabled(False)
        else:
            self.ui.searchEdit.setEnabled(True)
            self.ui.urlEdit.setEnabled(True)

    @Slot(int)
    def nsfwChanged(self, state):
        self.config.set('settings', 'nsfw', int(self.ui.nsfwCheckBox.isChecked()))
        self.updateVideosDisplay()

    @Slot(int)
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

    @Slot()
    def search(self):
        pattern = self.ui.searchEdit.text()
        if not pattern:
            return

        for minivideo in self.minivideos:
            self.ui.scrollAreaContent.layout().removeWidget(minivideo)
            minivideo.hide()
            minivideo.deleteLater()

        self.minivideos = []
        self.ui.searchEdit.setEnabled(False)

        backend_name = self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex())

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

    @Slot()
    def openURL(self):
        url = self.ui.urlEdit.text()
        if not url:
            return

        for backend in self.weboob.iter_backends():
            video = backend.get_video(url)
            if video:
                video_widget = Video(video, self)
                video_widget.show()

        self.ui.urlEdit.clear()

    def closeEvent(self, ev):
        self.config.set('settings', 'backend', self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()))
        self.config.set('settings', 'sortby', self.ui.sortbyEdit.currentIndex())
        self.config.save()
        ev.accept()

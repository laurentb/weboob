# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from PyQt4.QtCore import SIGNAL

from weboob.tools.application.qt import QtMainWindow

from weboob.frontends.qvideoob.ui.main_window_ui import Ui_MainWindow

from .video import Video
from .minivideo import MiniVideo

class MainWindow(QtMainWindow):
    def __init__(self, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.minivideos = []

        self.connect(self.ui.searchEdit, SIGNAL("returnPressed()"), self.search)
        self.connect(self.ui.urlEdit, SIGNAL("returnPressed()"), self.openURL)

    def search(self):
        pattern = unicode(self.ui.searchEdit.text())
        if not pattern:
            return

        for minivideo in self.minivideos:
            self.ui.scrollAreaContent.layout.removeWidget(minivideo)

        self.minivideos = []

        for backend in self.weboob.iter_backends():
            for video in backend.iter_search_results(pattern):
                minivideo = MiniVideo(backend, video)
                self.ui.scrollAreaContent.layout().addWidget(minivideo)
                self.minivideos.append(minivideo)

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



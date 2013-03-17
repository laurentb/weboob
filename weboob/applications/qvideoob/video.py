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


from PyQt4.QtCore import QUrl
from PyQt4.QtGui import QDialog
from PyQt4.phonon import Phonon

from weboob.applications.qvideoob.ui.video_ui import Ui_Video


class Video(QDialog):
    def __init__(self, video, parent=None):
        QDialog.__init__(self, parent)
        self.ui = Ui_Video()
        self.ui.setupUi(self)

        self.video = video
        self.setWindowTitle("Video - %s" % video.title)
        self.ui.urlEdit.setText(video.url)
        self.ui.titleLabel.setText(video.title)
        self.ui.durationLabel.setText(unicode(video.duration))
        self.ui.authorLabel.setText(unicode(video.author))
        self.ui.dateLabel.setText(unicode(video.date))
        if video.rating_max:
            self.ui.ratingLabel.setText('%s / %s' % (video.rating, video.rating_max))
        else:
            self.ui.ratingLabel.setText('%s' % video.rating)

        self.ui.seekSlider.setMediaObject(self.ui.videoPlayer.mediaObject())
        self.ui.videoPlayer.load(Phonon.MediaSource(QUrl(video.url)))
        self.ui.videoPlayer.play()

    def closeEvent(self, event):
        self.ui.videoPlayer.stop()
        event.accept()

    def hideEvent(self, event):
        self.ui.videoPlayer.stop()
        event.accept()

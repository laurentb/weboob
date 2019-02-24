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


from PyQt5.QtCore import QUrl, pyqtSlot as Slot
from PyQt5.QtWidgets import QDialog
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

from weboob.applications.qvideoob.ui.video_ui import Ui_Video
from weboob.tools.compat import unicode


class Video(QDialog):
    def __init__(self, video, parent=None):
        super(Video, self).__init__(parent)
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

        self.mediaPlayer = QMediaPlayer()

        self.mediaPlayer.durationChanged.connect(self._setMax)
        self.mediaPlayer.seekableChanged.connect(self.ui.seekSlider.setEnabled)
        self.mediaPlayer.positionChanged.connect(self._slide)
        self.ui.seekSlider.valueChanged.connect(self.mediaPlayer.setPosition)

        mc = QMediaContent(QUrl(video.url))
        self.mediaPlayer.setMedia(mc)
        self.ui.videoPlayer.setMediaObject(self.mediaPlayer)
        self.mediaPlayer.play()

    @Slot('qint64')
    def _slide(self, pos):
        blocking = self.ui.seekSlider.blockSignals(True)
        self.ui.seekSlider.setValue(pos)
        self.ui.seekSlider.blockSignals(blocking)

    @Slot('qint64')
    def _setMax(self, duration):
        self.ui.seekSlider.setMaximum(duration)

    def closeEvent(self, event):
        self.mediaPlayer.stop()
        event.accept()

    def hideEvent(self, event):
        self.mediaPlayer.stop()
        event.accept()

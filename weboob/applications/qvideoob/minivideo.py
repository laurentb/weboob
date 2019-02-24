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


from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QFrame

from weboob.tools.application.qt5 import QtDo
from weboob.tools.compat import unicode
from weboob.applications.qvideoob.ui.minivideo_ui import Ui_MiniVideo
from .video import Video


class MiniVideo(QFrame):
    def __init__(self, weboob, backend, video, parent=None):
        super(MiniVideo, self).__init__(parent)
        self.ui = Ui_MiniVideo()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.backend = backend
        self.video = video
        self.ui.titleLabel.setText(video.title)
        self.ui.backendLabel.setText(backend.name)
        self.ui.durationLabel.setText(unicode(video.duration))
        self.ui.authorLabel.setText(unicode(video.author))
        self.ui.dateLabel.setText(video.date and unicode(video.date) or '')
        if video.rating_max:
            self.ui.ratingLabel.setText('%s / %s' % (video.rating, video.rating_max))
        else:
            self.ui.ratingLabel.setText('%s' % video.rating)

        self.process_thumbnail = QtDo(self.weboob, self.gotThumbnail)
        self.process_thumbnail.do('fillobj', self.video, ['thumbnail'], backends=backend)

    def gotThumbnail(self, video):
        if video.thumbnail and video.thumbnail.data:
            img = QImage.fromData(video.thumbnail.data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        video = self.backend.fillobj(self.video)
        if video:
            video_widget = Video(video, self)
            video_widget.show()

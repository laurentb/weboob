# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import urllib2
from PyQt4.QtGui import QFrame, QImage, QPixmap

from weboob.applications.qvideoob.ui.minivideo_ui import Ui_MiniVideo
from .video import Video

class MiniVideo(QFrame):
    def __init__(self, backend, video, parent=None):
        QFrame.__init__(self, parent)
        self.ui = Ui_MiniVideo()
        self.ui.setupUi(self)

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

        if video.thumbnail_url:
            data = urllib2.urlopen(video.thumbnail_url).read()
            img = QImage.fromData(data)
            self.ui.imageLabel.setPixmap(QPixmap.fromImage(img))

    def enterEvent(self, event):
        self.setFrameShadow(self.Sunken)
        QFrame.enterEvent(self, event)

    def leaveEvent(self, event):
        self.setFrameShadow(self.Raised)
        QFrame.leaveEvent(self, event)

    def mousePressEvent(self, event):
        QFrame.mousePressEvent(self, event)

        video = self.backend.get_video(self.video.id)
        if video:
            video_widget = Video(video, self)
            video_widget.show()

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


from PyQt4.QtCore  import QUrl
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
        self.ui.durationLabel.setText('%d:%02d:%02d' % (video.duration/3600, (video.duration%3600)/60, video.duration%60))
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

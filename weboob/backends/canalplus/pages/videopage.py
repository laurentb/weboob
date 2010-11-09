# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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

from weboob.tools.browser import BasePage
from .video import CanalplusVideo
__all__ = ['VideoPage']

class VideoPage(BasePage):
    def on_loaded(self):
        pass
        
    def get_video(self, video, quality):
        if not video:
            video = CanalplusVideo(self.group_dict['id'])
        print quality
        print video.id
        for vid in self.document.getchildren():
            url = None
            lastest = None
            for format in vid[5][1].getchildren():
                if format.tag == quality:
                   url = format.text
                if format.text:
                    lastest = format
            if url == None:
                url = lastest.text
            video.url = url
            return video

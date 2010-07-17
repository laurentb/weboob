# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon
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


from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import ForbiddenVideo, ForbiddenVideoPage, VerifyAgePage, VideoPage
from .video import YoutubeVideo


__all__ = ['YoutubeBrowser']


class YoutubeBrowser(BaseBrowser):
    DOMAIN = u'youtube.com'
    ENCODING = None
    PAGES = {r'.*youtube\.com/watch\?v=(?P<id>.+)': VideoPage,
             r'.*youtube\.com/index\?ytsession=.+': ForbiddenVideoPage,
             r'.*youtube\.com/verify_age\?next_url=(?P<next_url>.+)': VerifyAgePage,
            }

    @id2url(YoutubeVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video)

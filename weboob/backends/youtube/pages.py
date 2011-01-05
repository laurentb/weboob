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


from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select


__all__ = ['ForbiddenVideo', 'ForbiddenVideoPage', 'VerifyAgePage', 'VideoPage']


class ForbiddenVideo(Exception):
    pass


class ForbiddenVideoPage(BasePage):
    def get_video(self, video=None):
        element = select(self.document.getroot(), '.yt-alert-content', 1)
        raise ForbiddenVideo(element.text.strip())


class VerifyAgePage(BasePage):
    def get_video(self, video=None):
        raise ForbiddenVideo('verify age not implemented')


class VideoPage(BasePage):
    pass

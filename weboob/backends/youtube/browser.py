# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz, Romain Bignon

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

import urllib

from weboob.tools.browser import BaseBrowser

from .pages import VideoPage

__all__ = ['YoutubeBrowser']

class YoutubeBrowser(BaseBrowser):
    PAGES = {'.*youtube\.com/watch\?v=(.+)': VideoPage,
            }

    def id2url(self, _id):
        return _id if 'youtube.com' in _id else 'http://www.youtube.com/watch?v=%s' % _id

    def get_video(self, _id):
        self.location(self.id2url(_id))
        return self.page.video

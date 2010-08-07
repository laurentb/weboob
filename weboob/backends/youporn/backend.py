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


from __future__ import with_statement

import os

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend

from .browser import YoupornBrowser
from .video import YoupornVideo


__all__ = ['YoupornBackend']


class YoupornBackend(BaseBackend, ICapVideo):
    NAME = 'youporn'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.1'
    DESCRIPTION = 'Youporn videos website'
    LICENSE = 'GPLv3'
    ICON = os.path.join(os.path.dirname(__file__), 'data/logo.png')

    BROWSER = YoupornBrowser

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    SORTBY = ['relevance', 'rating', 'views', 'time']
    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False):
        if not nsfw:
            return set()
        with self.browser:
            return self.browser.iter_search_results(pattern, self.SORTBY[sortby])

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(YoupornVideo.id2url(video.id), video)
        if 'thumbnail' in fields:
            with self.browser:
                video.thumbnail.data = self.browser.openurl(video.thumbnail.url).read()

        return video

    OBJECTS = {YoupornVideo: fill_video}

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


from __future__ import with_statement

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import CanalplusBrowser
from .pages import CanalplusVideo

from weboob.capabilities.collection import ICapCollection


__all__ = ['CanalplusBackend']


class CanalplusBackend(BaseBackend, ICapVideo, ICapCollection):
    NAME = 'canalplus'
    MAINTAINER = 'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '0.8'
    DESCRIPTION = 'Canal plus french TV'
    LICENSE = 'GPLv3'
    CONFIG = ValuesDict(Value('quality', label='Quality of videos', choices=['hd', 'sd'], default='hd'))
    BROWSER = CanalplusBrowser

    def create_default_browser(self):
        return self.create_browser(quality=self.config['quality'])

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=None):
        with self.browser:
            return self.browser.iter_search_results(pattern)

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(CanalplusVideo.id2url(video.id), video)
        if 'thumbnail' in fields:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)
        return video

    OBJECTS = {CanalplusVideo: fill_video}
    
    working_coll = []
    
    def get_working_collection(self):
        return self.working_coll
    
    def change_working_collection(self, splited_path):
        self.working_coll = self.browser.change_working_collection(splited_path)
        return self.working_coll
        
    def iter_resources(self):
        rep = self.browser.iter_resources(self.working_coll)
        return rep

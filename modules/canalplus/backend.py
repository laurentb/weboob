# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from __future__ import with_statement

import re

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import Value

from .browser import CanalplusBrowser
from .pages import CanalplusVideo

from weboob.capabilities.collection import ICapCollection


__all__ = ['CanalplusBackend']


class CanalplusBackend(BaseBackend, ICapVideo, ICapCollection):
    NAME = 'canalplus'
    MAINTAINER = 'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '0.a'
    DESCRIPTION = 'Canal plus french TV'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('quality', label='Quality of videos', choices=['hd', 'sd'], default='hd'))
    BROWSER = CanalplusBrowser

    def create_default_browser(self):
        return self.create_browser(quality=self.config['quality'].get())

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=None):
        with self.browser:
            return self.browser.iter_search_results(pattern)

    def get_video(self, _id):
        m = re.match('https?://www\.canal-?plus\.fr/.*\?vid=(\d+)', _id)
        if m:
            _id = m.group(1)
        with self.browser:
            return self.browser.get_video(_id)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(CanalplusVideo.id2url(video.id), video)
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)
        return video

    OBJECTS = {CanalplusVideo: fill_video}

    def iter_resources(self, split_path):
        with self.browser:
            return self.browser.iter_resources(split_path)

# -*- coding: utf-8 -*-

# Copyright(C) 2015      P4ncake
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.backend import Module
from weboob.capabilities.video import CapVideo

from .browser import VineBrowser


__all__ = ['VineModule']


class VineModule(Module, CapVideo):
    NAME = 'vine'
    DESCRIPTION = u'vine website'
    MAINTAINER = u'P4ncake'
    EMAIL = 'me@p4ncake.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = VineBrowser

    def search_videos(self, pattern, nsfw=False):
        return self.browser.search_videos(pattern)

    def get_video(self, _id):
        return self.browser.get_video(_id=_id)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            video = self.browser.get_video(video.id, video)
        if 'thumbnail' in fields and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content

        return video


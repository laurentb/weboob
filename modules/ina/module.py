# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.audio import CapAudio, BaseAudio, decode_id

from weboob.tools.backend import Module

from .browser import InaBrowser

__all__ = ['InaModule']


class InaModule(Module, CapVideo, CapAudio):
    NAME = 'ina'
    MAINTAINER = u'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '1.5'
    DESCRIPTION = 'INA French TV video archives'
    LICENSE = 'AGPLv3+'
    BROWSER = InaBrowser

    def get_video(self, _id):
        return self.browser.get_video(_id)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern)

    def fill_media(self, media, fields):
        if fields != ['thumbnail'] and fields != ['url']:
            # if we don't want only the thumbnail, we probably want also every fields
            if isinstance(media, BaseVideo):
                media = self.browser.get_video(media.id, media)
            else:
                _id = BaseAudio.decode_id(media.id)
                media = self.browser.get_audio(_id, media)
        if 'url' in fields and not media.url:
            _id = BaseAudio.decode_id(media.id) if isinstance(media, BaseAudio) else media.id
            media.url = self.browser.get_media_url(_id)
        if 'thumbnail' in fields and media.thumbnail:
            media.thumbnail.data = self.browser.open(media.thumbnail.url).content
        return media

    def search_audio(self, pattern, sortby=CapAudio.SEARCH_RELEVANCE):
        return self.browser.search_audio(pattern)

    @decode_id(BaseAudio.decode_id)
    def get_audio(self, _id):
        return self.browser.get_audio(_id)

    OBJECTS = {BaseVideo: fill_media, BaseAudio: fill_media}

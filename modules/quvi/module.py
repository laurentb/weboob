# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

# sample usage: youtube.XXXXXX@quvi
# or also: https://www.youtube.com/watch?v=XXXXXX@quvi
# shortened URLs are also supported

# this backend requires the quvi 0.4 C library to be installed


import datetime
from weboob.capabilities.base import UserError, StringField
from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.image import Thumbnail
from weboob.tools.backend import Module
from weboob.tools.misc import to_unicode

from .quvi import LibQuvi, QuviError


__all__ = ['QuviModule', 'QuviVideo']


class QuviModule(Module, CapVideo):
    NAME = 'quvi'
    DESCRIPTION = u'Multi-website video helper with quvi. Handles Youtube, BBC, and a lot more'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = None

    def get_video(self, _id):
        video = QuviVideo(_id)

        parser = LibQuvi()
        if not parser.load():
            raise UserError('Make sure libquvi 0.4 is installed')

        try:
            info = parser.get_info(video.page_url)
        except QuviError as qerror:
            raise UserError(qerror.message)

        video.url = to_unicode(info.get('url'))
        if not video.url:
            raise NotImplementedError()

        video.ext = to_unicode(info.get('suffix'))
        video.title = to_unicode(info.get('title'))
        video.page = to_unicode(info.get('page'))
        duration = int(info.get('duration', 0))
        if duration:
            video.duration = datetime.timedelta(milliseconds=duration)
        if info.get('thumbnail'):
            video.thumbnail = Thumbnail(info.get('thumbnail'))
            video.thumbnail.url = video.thumbnail.id
        return video


class QuviVideo(BaseVideo):
    BACKENDS = {
        'youtube': 'https://www.youtube.com/watch?v=%s',
        'vimeo': 'http://vimeo.com/%s',
        'dailymotion': 'http://www.dailymotion.com/video/%s',
        'metacafe': 'http://www.metacafe.com/watch/%s/',
        'arte': 'http://videos.arte.tv/fr/videos/plop--%s.html',
        'videa': 'http://videa.hu/videok/%s/',
        'wimp': 'http://www.wimp.com/%s/',
        'funnyordie': 'http://www.funnyordie.com/videos/%s/',
        'tapuz': 'http://flix.tapuz.co.il/v/watch-%s-.html',
        'liveleak': 'http://www.liveleak.com/view?i=%s',
        # nsfw
        'xhamster': 'https://xhamster.com/movies/%s/plop.html',
        'xvideos': 'http://www.xvideos.com/video%s/',
        'redtube': 'http://www.redtube.com/%s',
        'xnxx': 'http://video.xnxx.com/video%s/',
        # more websites are supported, but <service>.<id> isn't always enough
        # however, URLs are supported, like this:
        # https://www.youtube.com/watch?v=BaW_jenozKc@quvi
    }

    page = StringField('Page URL of the video')

    @classmethod
    def id2url(cls, _id):
        if _id.startswith('http'):
            return _id

        if '.' not in _id:
            raise UserError('Please give an ID in form WEBSITE.ID (for example youtube.BaW_jenozKc). Supported websites are: %s' % ', '.join(cls.BACKENDS.keys()))

        sub_backend, sub_id = _id.split('.', 1)
        try:
            return cls.BACKENDS[sub_backend] % sub_id
        except KeyError:
            raise NotImplementedError()

    @property
    def page_url(self):
        if self.page:
            return self.page
        else:
            return self.id2url(self.id)

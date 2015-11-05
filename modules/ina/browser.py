# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


from weboob.browser import PagesBrowser, URL
from .pages import SearchPage, MediaPage, RssPage

__all__ = ['InaBrowser']


class InaBrowser(PagesBrowser):
    BASEURL = 'http://www.ina.fr/'

    search_page = URL('layout/set/ajax/recherche/result\?q=(?P<pattern>.*)&autopromote=&b=(?P<first_item>.*)&type=(?P<type>(Audio|Video))&r=', SearchPage)
    media_page = URL('/(?P<type>(audio|video))/(?P<_id>.*)', MediaPage)
    rss_page = URL('https://player.ina.fr/notices/(?P<_id>.*).mrss', RssPage)

    def get_video(self, _id, video=None):
        if not video:
            video = self.media_page.go(_id=_id, type='video').get_video(obj=video)

        video.url = self.get_media_url(_id)
        return video

    def get_media_url(self, _id):
        return self.rss_page.go(_id=_id).get_media_url()

    def search_videos(self, pattern):
        return self.search_page.go(pattern=pattern.encode('utf-8'),
                                   type='Video',
                                   first_item='0').iter_videos()

    def get_audio(self, _id, audio=None):
        if not audio:
            audio = self.media_page.go(_id=_id, type='audio').get_audio(obj=audio)
        audio.url = self.get_media_url(_id)
        return audio

    def search_audio(self, pattern):
        return self.search_page.go(pattern=pattern.encode('utf-8'),
                                   type='Audio',
                                   first_item='0').iter_audios()

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Roger Philibert
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


import re

from weboob.tools.browser2.page import method, HTMLPage
from weboob.tools.browser2.elements import ItemElement
from weboob.tools.browser2.filters import CleanText, Env, Duration
from weboob.capabilities.video import BaseVideo
from weboob.tools.misc import to_unicode


__all__ = ['VideoPage']


class VideoPage(HTMLPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Env('id')
        obj_title = CleanText('//title')
        obj_nsfw = True
        obj_ext = u'flv'
        obj_duration = CleanText('//div[@id="video_text"]') & Duration

        def obj_url(self):
            real_id = int(self.env['id'].split('-')[-1])
            response = self.page.browser.open('http://www.youjizz.com/videos/embed/%s' % real_id)
            data = response.text

            video_file_urls = re.findall(r'"(http://[^",]+\.youjizz\.com[^",]+\.flv(?:\?[^"]*)?)"', data)
            if len(video_file_urls) == 0:
                raise ValueError('Video URL not found')
            elif len(video_file_urls) > 1:
                raise ValueError('Many video file URL found')
            else:
                return to_unicode(video_file_urls[0])

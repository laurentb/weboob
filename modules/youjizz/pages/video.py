# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Roger Philibert
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


import re

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, method
from weboob.browser.filters.standard import CleanText, Env
from weboob.capabilities.video import BaseVideo
from weboob.tools.misc import to_unicode


class VideoPage(HTMLPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Env('id')
        obj_title = CleanText('//title')
        obj_nsfw = True
        obj_ext = u'flv'

        def obj_url(self):
            real_id = int(self.env['id'].split('-')[-1])
            response = self.page.browser.open('https://www.youjizz.com/videos/embed/%s' % real_id)
            data = response.text

            video_file_urls = re.findall(r'"((?:https?:)?//[^",]+\.(?:flv|mp4)(?:\?[^"]*)?)"', data.replace('\\', ''))
            if len(video_file_urls) == 0:
                raise ValueError('Video URL not found')

            url = to_unicode(video_file_urls[-1])
            if url.startswith('//'):
                url = u'https:' + url
            return url

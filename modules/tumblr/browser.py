# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

import re

from weboob.tools.json import json
from weboob.browser.browsers import APIBrowser
from weboob.browser.filters.standard import CleanText
from weboob.capabilities.gallery import BaseImage
from weboob.capabilities.image import Thumbnail


class TumblrBrowser(APIBrowser):
    def __init__(self, baseurl, *args, **kwargs):
        super(TumblrBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = baseurl

    def request(self, *args, **kwargs):
        # JSONP
        r = super(TumblrBrowser, self).open(*args, **kwargs).text
        r = re.sub(r'^var tumblr_api_read = (.*);$', r'\1', r)
        return json.loads(r)

    def get_title(self):
        r = self.request('/api/read/json?type=photo&num=1&start=0&filter=text')
        return r['tumblelog']['title']

    def iter_images(self, gallery):
        index = 0
        offset = 0
        step = 50

        while True:
            r = self.request('/api/read/json?type=photo&filter=text', params={'start': offset, 'num': step})
            for post in r['posts']:
                # main photo only if single
                if not post['photos']:
                    img = BaseImage(
                        index=index,
                        gallery=gallery,
                        url=post['photo-url-1280'],
                        thumbnail=Thumbnail(post['photo-url-250']),
                    )
                    index += 1
                    img.title = CleanText().filter(post['photo-caption'])
                    #img.date = post['date-gmt']
                    img._page_url = post["url"]
                    yield img

                # if multiple
                for photo in post['photos']:
                    img = BaseImage(
                        index=index,
                        gallery=gallery,
                        url=photo['photo-url-1280'],
                        thumbnail=Thumbnail(photo['photo-url-250']),
                    )
                    index += 1
                    img.title = CleanText().filter(photo['caption'] or post['photo-caption'])
                    #img.date = post['date-gmt']
                    img._page_url = post["url"]
                    yield img

            offset += step
            if not r['posts'] or offset >= r['posts-total']:
                break

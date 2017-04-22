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


from weboob.browser import PagesBrowser, URL
from weboob.capabilities.gallery import BaseImage

from .pages import MainPage, FramePage


class TumblrBrowser(PagesBrowser):
    main = URL(r'/page/(?P<page>\d+)', MainPage)
    frame = URL(r'/post/.*/photoset_iframe/.*', r'https?://www.tumblr.com/video/.*/', FramePage)

    def __init__(self, baseurl, *args, **kwargs):
        super(TumblrBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = baseurl

    def iter_images(self, gallery):
        page = 0
        index = 0
        empty = 0

        for page in xrange(1000):
            if page == 1:
                continue # page 1 doesn't exist, don't ask why

            self.main.go(page=page)

            empty += 1
            for url in self.page.get_content():
                img = BaseImage(url, index=index, gallery=gallery)
                img.url = url
                yield img
                index += 1
                empty = 0

            if empty > 10:
                self.logger.warning("10 empty pages, considering it's the end")
                break

        else:
            assert False, "that's a lot of pages, misdetected end?"

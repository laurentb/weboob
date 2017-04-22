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

from weboob.browser.pages import HTMLPage


class MainPage(HTMLPage):
    def get_content(self):
        expr = ' | '.join([
            '//iframe[has-class("tumblr_video_iframe") or @class="photoset"]',
            '//div[@class="photo-wrapper-inner"]/img',
            '//div[@class="media"]/img',
            '//div[has-class("post-content")]//img',
            '//div[has-class("gridphoto")]',
        ])
        for item in self.doc.xpath(expr):
            if item.tag == 'iframe':
                for obj in self.browser.open(item.attrib['src']).page.get_content():
                    yield obj
            elif item.tag == 'img':
                for attr in ('data-highres', 'src'):
                    if attr in item.attrib:
                        yield item.attrib[attr]
                        break
            elif item.tag == 'div':
                if 'data-photo-high' in item.attrib:
                    yield item.attrib['data-photo-high']


class FramePage(HTMLPage):
    def get_content(self):
        for item in self.doc.xpath('//a[has-class("photoset_photo")]/img'):
            yield item.attrib['src']

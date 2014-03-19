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

from weboob.tools.browser2 import HTMLPage
from weboob.tools.browser2.page import ListElement, method, ItemElement
from weboob.tools.browser2.filters import Filter, Link, CleanText, Duration
from weboob.capabilities.image import BaseImage
from weboob.capabilities.video import BaseVideo


__all__ = ['IndexPage']


class IndexPage(HTMLPage):
    @method
    class iter_videos(ListElement):
        item_xpath = '//span[@id="miniatura"]'

        next_page = Link(u'//a[text()="Next »"]')

        class item(ItemElement):
            klass = BaseVideo

            class Id(Filter):
                def filter(self, link):
                    return re.sub(r'/videos/(.+)\.html', r'\1', link)

            obj_id = Id(Link('.//a'))
            obj_title = CleanText('.//span[@id="title1"]')
            obj_duration = Duration(CleanText('.//span[@class="thumbtime"]//span'))
            obj_nsfw = True

            def obj_thumbnail(self):
                thumbnail = BaseImage(self.xpath('.//img')[0].attrib['data-original'])
                thumbnail.url = thumbnail.id
                return thumbnail

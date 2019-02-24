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


from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Duration, Regexp
from weboob.browser.filters.html import Link, CSS
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo


class IndexPage(HTMLPage):
    @pagination
    @method
    class iter_videos(ListElement):
        item_xpath = '//span[@id="miniatura"]'

        next_page = Link(u'//a[text()="Next »"]')

        class item(ItemElement):
            klass = BaseVideo

            obj_id = CSS('a') & Link & Regexp(pattern=r'/videos/(.+)\.html')
            obj_title = CSS('span#title1') & CleanText
            obj_duration = CSS('span.thumbtime span') & CleanText & Duration | NotAvailable
            obj_nsfw = True

            def obj_thumbnail(self):
                thumbnail = Thumbnail(self.xpath('.//img')[0].attrib['data-original'])
                thumbnail.url = thumbnail.id.replace('http://', 'https://')
                return thumbnail

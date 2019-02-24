# -*- coding: utf-8 -*-

# Copyright(C) 2016 Roger Philibert
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


from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.html import Link, CSS, Attr
from weboob.browser.filters.standard import CleanText, Duration, Regexp, Env
from weboob.browser.pages import HTMLPage, pagination
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo


class IndexPage(HTMLPage):
    @pagination
    @method
    class iter_videos(ListElement):
        item_xpath = '//li[has-class("videoblock")]'

        next_page = Link(u'//a[text()="Next"]')

        class item(ItemElement):
            klass = BaseVideo

            obj_id = CSS('a') & Link & Regexp(pattern=r'viewkey=(.+)')
            obj_title = Attr('.//span[has-class("title")]/a', 'title') & CleanText
            obj_duration = CSS('var.duration') & CleanText & Duration | NotAvailable
            obj_nsfw = True

            def obj_thumbnail(self):
                thumbnail = Thumbnail(Attr('.//img[has-class("js-videoThumb")]', 'data-path')(self).replace('{index}', '1'))
                thumbnail.url = thumbnail.id
                return thumbnail


class VideoPage(HTMLPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Env('id')
        obj_title = CleanText('//title')
        obj_nsfw = True
        obj_ext = u'mp4'
        obj_url = CleanText('//script') & Regexp(pattern=r'(https:\\/\\/[^"]+\.mp4[^"]+)"') & CleanText(replace=[('\\', '')])

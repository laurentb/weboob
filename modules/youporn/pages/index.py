# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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



from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.html import Attr
from weboob.browser.filters.standard import CleanText, Duration, Regexp, Type
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import Thumbnail

from ..video import YoupornVideo


class IndexPage(HTMLPage):
    @method
    class iter_videos(ListElement):
        item_xpath = '//div[has-class("video-box")]'

        class item(ItemElement):
            klass = YoupornVideo

            def obj_thumbnail(self):
                thumbnail_url = Attr('.//img', 'data-original')(self)
                thumbnail = Thumbnail(thumbnail_url)
                thumbnail.url = thumbnail.id
                return thumbnail

            obj_author = NotAvailable
            obj_duration = CleanText('.//div[has-class("video-duration")]') & Duration()
            obj_id = Attr('.', 'data-video-id')
            obj_rating = CleanText('.//span[has-class("video-box-percentage")]') & Regexp(pattern=r'(\d+)%') & Type(type=int)
            obj_rating_max = 100
            obj_title = CleanText('.//div[has-class("video-box-title")]')

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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

from weboob.capabilities.video import BaseVideo
from weboob.capabilities.image import Thumbnail
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.pages import HTMLPage, pagination, JsonPage
from weboob.browser.filters.standard import Regexp, CleanText
from weboob.browser.filters.json import Dict


class ListPage(HTMLPage):
    def get_token(self):
        return Regexp(CleanText('//script'), '"jwt":"(.*)","url"', default=None)(self.doc)


class APIPage(JsonPage):
    @pagination
    @method
    class iter_videos(DictElement):
        item_xpath = 'data'

        next_page = Dict('paging/next')

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Regexp(Dict('clip/uri'), '/videos/(.*)')
            obj_title = Dict('clip/name')

            def obj_thumbnail(self):
                thumbnail = Thumbnail(Dict('clip/pictures/sizes/0/link')(self))
                thumbnail.url = thumbnail.id
                return thumbnail

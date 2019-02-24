# -*- coding: utf-8 -*-

# Copyright(C) 2015      P4ncake
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

from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.pages import JsonPage
from weboob.browser.filters.standard import Regexp
from weboob.browser.filters.json import Dict


class SearchPage(JsonPage):
    @method
    class iter_videos(DictElement):
        item_xpath ='data/records'
        class item(ItemElement):
            klass = BaseVideo

            obj_id = Regexp(Dict('shareUrl'), '/([a-zA-Z0-9]*)$')
            obj_title = Dict('description')
            obj_url = Dict('videoUrl')
            obj_ext = Regexp(Dict('videoUrl'), r'.*\.(.*?)\?.*')
            obj_author = Dict('username')

class PostPage(JsonPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Dict('postId')
        obj_url = Dict('videoUrl')

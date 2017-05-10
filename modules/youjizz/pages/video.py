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


from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, method
from weboob.browser.filters.standard import CleanText, Env, Async, AsyncLoad, Regexp, Format
from weboob.browser.filters.html import Attr
from weboob.capabilities.video import BaseVideo


class VideoPage(HTMLPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Env('id')
        obj_title = CleanText('//title')
        obj_nsfw = True
        obj_ext = u'flv'

        load_url = Format('https://www.youjizz.com/videos/embed/%s', Regexp(Env('id'), '.*-(.+)$')) & AsyncLoad
        obj_url = Async('url') & Format('https:%s', Attr('(//div[has-class("desktop-only")]/video//source)[last()]', 'src'))

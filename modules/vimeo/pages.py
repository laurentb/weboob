# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.image import BaseImage

from weboob.exceptions import ParseError
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, pagination, JsonPage
from weboob.browser.filters.standard import Regexp, Env, CleanText, DateTime, Duration, Field
from weboob.browser.filters.html import Attr, Link

import re


class VimeoDuration(Duration):
    regexp = re.compile(r'(?P<hh>\d+)H(?P<mm>\d+)M(?P<ss>\d+)S')


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_videos(ListElement):
        item_xpath = '//div[@id="browse_content"]/ol/li'

        next_page = Link(u'//a[text()="Next"]')

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Regexp(Attr('.', 'id'), 'clip_(.*)')
            obj_title = Attr('./a', 'title')

            def obj_thumbnail(self):
                thumbnail = BaseImage(self.xpath('./a/img')[0].attrib['src'])
                thumbnail.url = thumbnail.id
                return thumbnail


class VideoPage(HTMLPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        _balise = lambda x: '//div[@itemprop="video"]/meta[@itemprop="%s"]/@content' % x

        obj_id = Env('_id')
        obj_title = CleanText(_balise('name'))
        obj_date = DateTime(CleanText(_balise('dateCreated')))
        obj_duration = VimeoDuration(CleanText(_balise('duration')))
        obj_description = CleanText(_balise('description'))
        obj_author = CleanText('//div[@itemprop="author"]/meta[@itemprop="name"]/@content')

        def obj_thumbnail(self):
            thumbnail = BaseImage(CleanText('//div[@itemprop="video"]/span[@itemprop="thumbnail"]/link/@href')(self.el))
            thumbnail.url = thumbnail.id
            return thumbnail


class VideoJsonPage(JsonPage):
    @method
    class fill_url(ItemElement):
        klass = BaseVideo

        def obj_url(self):
            quality = 'sd'
            codec = None
            data = self.el
            if 'vp6' in data['request']['files']:
                codec = 'vp6'
            if 'vp8' in data['request']['files']:
                codec = 'vp8'
            if 'h264' in data['request']['files']:
                codec = 'h264'
            if not codec:
                raise ParseError('Unable to detect available codec for id: %r' % int(Field('id')(self)))
            if 'hd' in data['request']['files'][codec]:
                quality = 'hd'
            return data['request']['files'][codec][quality]['url']

        obj_ext = Regexp(Field('url'), '.*\.(.*?)\?.*')

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
from weboob.capabilities.collection import Collection

from weboob.exceptions import ParseError
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, pagination, JsonPage
from weboob.browser.filters.standard import Regexp, Env, CleanText, DateTime, Duration, Field, Type
from weboob.browser.filters.html import Attr, Link, CleanHTML, XPath
from weboob.browser.filters.json import Dict

import re


class VimeoDuration(Duration):
    _regexp = re.compile(r'PT(?P<hh>\d+)H(?P<mm>\d+)M(?P<ss>\d+)S')


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
    def __init__(self, *args, **kwargs):
        super(VideoPage, self).__init__(*args, **kwargs)
        from weboob.tools.json import json
        jsoncontent = XPath('//script[@type="application/ld+json"]/text()')(self.doc)[0]
        self.doc = json.loads(jsoncontent)[0]

    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Env('_id')
        obj_title = CleanText(Dict('name'))
        obj_description = CleanHTML(Dict('description'))
        obj_date = DateTime(Dict('datePublished'))
        obj_duration = VimeoDuration(Dict('duration'))
        obj_author = CleanText(Dict('author/name'))
        obj_nsfw = Type(Dict('isFamilyFriendly'), type=bool)

        def obj_thumbnail(self):
            thumbnail = BaseImage(Dict('thumbnailUrl')(self.el))
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


class CategoriesPage(HTMLPage):
    @method
    class iter_categories(ListElement):
        item_xpath = '//div[@class="category_grid"]/div/a'

        class item(ItemElement):
            klass = Collection

            obj_id = CleanText('./@href')
            obj_title = CleanText('./div/div/p')

            def obj_split_path(self):
                split_path = ['vimeo-categories']
                category = CleanText('./@href', replace=[('/categories/', '')])(self)
                split_path.append(category)
                return split_path


class ChannelsPage(HTMLPage):
    @pagination
    @method
    class iter_channels(ListElement):
        item_xpath = '//div[@id="browse_content"]/ol/li'
        next_page = Link('//li[@class="pagination_next"]/a')

        class item(ItemElement):
            klass = Collection

            obj_title = CleanText('div/a/div/p[@class="title"]')
            obj_id = CleanText('./@id')

            def obj_split_path(self):
                split_path = ['vimeo-channels']
                channel = CleanText('div/a/@href', replace=[('/channels/', '')])(self)
                split_path.append(channel)
                return split_path

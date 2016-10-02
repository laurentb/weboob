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
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.collection import Collection

from weboob.exceptions import ParseError
from weboob.browser.elements import ItemElement, ListElement, method, DictElement
from weboob.browser.pages import HTMLPage, pagination, JsonPage
from weboob.browser.filters.standard import Regexp, Env, CleanText, DateTime, Duration, Field, BrowserURL
from weboob.browser.filters.html import Attr, Link, CleanHTML, XPath
from weboob.browser.filters.json import Dict

import re


class VimeoDuration(Duration):
    _regexp = re.compile(r'PT(?P<hh>\d+)H(?P<mm>\d+)M(?P<ss>\d+)S')


class ListPage(HTMLPage):
    def get_token(self):
        return Regexp(CleanText('//script'), '"jwt":"(.*)","url"', default=None)(self.doc)

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
                thumbnail = Thumbnail(self.xpath('./a/img')[0].attrib['src'])
                thumbnail.url = thumbnail.id
                return thumbnail


class APIPage(JsonPage):
    @pagination
    @method
    class iter_videos(DictElement):
        item_xpath = 'data'

        def parse(self, el):
            self.env['next_page'] = Regexp(Dict('paging/next'), 'page=(\d*)', default=None)(el)

        def next_page(self):
            if Env('next_page')(self) is not None:
                return BrowserURL('api_page', page=int(Env('next_page')(self)), category=Env('category'))(self)

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Regexp(Dict('clip/uri'), '/videos/(.*)')
            obj_title = Dict('clip/name')

            def obj_thumbnail(self):
                thumbnail = Thumbnail(Dict('clip/pictures/sizes/0/link')(self))
                thumbnail.url = thumbnail.id
                return thumbnail


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_videos(ListElement):
        item_xpath = '//ul[@class="small-block-grid-3"]/li/div[has-class("clip_thumbnail")]'
        ignore_duplicate = True
        next_page = Link(u'//a[text()="Next"]')

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Attr('.', 'data-clip-id')
            obj_title = Attr('./a/span', 'title')

            def obj_thumbnail(self):
                thumbnail = Thumbnail(self.xpath('./a/div/img')[0].attrib['src'])
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
        obj_title = CleanText(CleanHTML(Dict('name')))
        obj_description = CleanHTML(Dict('description'))
        obj_date = DateTime(Dict('uploadDate'))
        obj_duration = VimeoDuration(Dict('duration'))
        obj_author = CleanText(Dict('author/name'))

        def obj_nsfw(self):
            _sfw = Dict('isFamilyFriendly', default="True")(self)
            return _sfw != "True"

        def obj_thumbnail(self):
            thumbnail = Thumbnail(Dict('thumbnailUrl')(self.el))
            thumbnail.url = thumbnail.id
            return thumbnail


class VideoJsonPage(JsonPage):
    @method
    class fill_url(ItemElement):
        klass = BaseVideo

        def obj_url(self):
            data = self.el

            if not data['request']['files']:
                raise ParseError('Unable to detect any stream method for id: %r (available: %s)'
                                 % (int(Field('id')(self)),
                                    data['request']['files'].keys()))

            # Choosen method is not available, we choose an other one
            method = self.obj._method
            if method not in data['request']['files']:
                method = data['request']['files'].keys()[0]

            streams = data['request']['files'][method]
            if not streams:
                raise ValueError('There is no url available for id: %r' % (int(Field('id')(self))))

            # stream is single for hls, just return the url
            stream = streams['url'] if method == 'hls' else None

            # ...but a list for progressive
            # we assume the list is sorted by quality with best first
            if not stream:
                quality = self.obj._quality
                stream = streams[quality]['url'] if quality < len(streams) else streams[0]['url']

            return stream

        obj_ext = Regexp(Field('url'), '.*\.(.*)\?.*$', '\\1')


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

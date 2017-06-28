# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from datetime import timedelta

from weboob.capabilities.image import Thumbnail
from weboob.capabilities.base import BaseObject, NotAvailable
from weboob.capabilities.collection import Collection
from weboob.capabilities.base import empty
from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import DictElement, ItemElement, ListElement, method
from weboob.browser.filters.standard import Date, Format, Env, CleanText, Field, Regexp, Join, Eval
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import XPath
from weboob.tools.compat import basestring, unquote

from .video import ArteVideo, ArteSiteVideo, SITE


class ArteItemElement(ItemElement):

    def condition(self):
        return 'VID' in self.el

    obj_id = Dict('VID')

    def obj_title(self):
        vti = Dict('VTI')(self)
        vtu = Dict('VSU', default=None)(self)
        if not vtu:
            return vti

        return '%s: %s' % (vti, vtu)

    obj_rating = Dict('VRT', default=NotAvailable)
    obj_rating_max = 10
    obj_description = Dict('VDE', default=NotAvailable)
    obj_date = Date(Dict('VDA', default=NotAvailable), default=NotAvailable)

    def obj_duration(self):
        seconds = Dict('videoDurationSeconds', default=NotAvailable)(self)
        if empty(seconds):
            return seconds
        elif isinstance(seconds, basestring):
            seconds = int(seconds)

        return timedelta(seconds=seconds)

    def obj_thumbnail(self):
        url = Dict('VTU/IUR', default=NotAvailable)(self)
        if empty(url):
            return url

        thumbnail = Thumbnail(url)
        thumbnail.url = thumbnail.id
        return thumbnail


class VideosListPage(HTMLPage):

    @method
    class iter_arte_concert_categories(ListElement):
        item_xpath = '//ul[@class="filter-liste"]/li'

        class item(ItemElement):
            klass = Collection

            obj_title = CleanText('./a/span')
            obj_id = CleanText('./@data-target', replace=[('video_box_tab_', '')])

            def obj_split_path(self):
                _id = CleanText('./@data-target', replace=[('video_box_tab_', '')])(self)
                return [SITE.CONCERT.get('id'), u'%s' % _id]

    @method
    class iter_arte_concert_videos(ListElement):

        def find_elements(self):
            self.item_xpath = '//div[@id="video_box_tab_%s"]/article' % Env('cat')(self)
            for el in self.el.xpath(self.item_xpath):
                yield el

        class item(ItemElement):
            klass = ArteSiteVideo

            obj__site = SITE.CONCERT.get('id')
            obj_id = Format('%s.%s', Field('_site'), CleanText('./@about'))
            obj_title = CleanText('div/div[@class="info-article "]/div/h3/a')

            def obj_thumbnail(self):
                url = CleanText('div/div/a/figure/span/span/@data-src')(self)
                thumbnail = Thumbnail(url)
                thumbnail.url = thumbnail.id
                return thumbnail

    @method
    class iter_arte_creative_categories(ListElement):
        item_xpath = '//ul[@class="menu"]/li/a[not(@target)]'

        class item(ItemElement):
            klass = Collection

            obj_title = CleanText('.', default=u'Accueil')
            obj_id = CleanText('./@href')

            def obj_split_path(self):
                _id = Regexp(CleanText('./@href'), '/\w{2}/(.*)', default=u'accueil')(self)
                return [SITE.CREATIVE.get('id')] + [_id.replace('/', '^')]

    @method
    class iter_arte_creative_videos(ListElement):
        item_xpath = '//div[div/i]'
        ignore_duplicate = True

        class item(ItemElement):
            klass = ArteSiteVideo

            obj__site = SITE.CREATIVE.get('id')
            obj_id = Format('%s.%s', Field('_site'),
                            CleanText('./div/h3/a/@href|./div/h1/a/@href'))
            obj_title = CleanText('./div/h3/a|./div/h1/a')

            def obj_thumbnail(self):
                url = CleanText('./div/a/img/@src')(self)
                thumbnail = Thumbnail(url)
                thumbnail.url = thumbnail.id
                return thumbnail

    @method
    class iter_arte_cinema_categories(ListElement):
        item_xpath = '//li[has-class("leaf")]'

        class item(ItemElement):
            klass = Collection

            def condition(self):
                return Regexp(CleanText('./a/@href'), '^(/\w{2}/%s/.*)' % self.env['cat'], default=None)(self)

            obj_title = CleanText('./a')
            obj_id = CleanText('./a/@href')

            def obj_split_path(self):
                _id = Regexp(CleanText('./a/@href'), '/\w{2}/(.*)')(self)
                return [SITE.CINEMA.get('id')] + _id.split('/')

    def get_arte_cinema_menu(self):
        return self.doc.xpath('//li[has-class("leaf")]/a[starts-with(@href,"/")]/@href')

    @method
    class get_arte_cinema_videos(ListElement):
        item_xpath = '//div[has-class("article-list")]/article[@id]'

        class item(ItemElement):
            klass = ArteSiteVideo

            def condition(self):
                return len(XPath('.//div[@class="article-secondary "]')(self)) == 1

            obj__site = SITE.CINEMA.get('id')
            obj_id = Format('%s.%s', Field('_site'),
                            Regexp(CleanText('./div/div/a/@href|./div/a/@href'),
                                   '(http://.*\.arte\.tv)?/(.*)',
                                   '\\2'))
            obj_title = Join(u' - ',
                             './/div[@class="article-secondary "]/div/div')

            def obj_thumbnail(self):
                url = CleanText('.//div[@class="article-primary "]/div[has-class("field-thumbnail")]/span/noscript/img/@src')(self)
                thumbnail = Thumbnail(url)
                thumbnail.url = thumbnail.id
                return thumbnail

    def get_json_url(self):
        if self.doc.xpath('//div[@class="video-container"]'):
            return self.doc.xpath('//div[@class="video-container"]')[0].attrib['arte_vp_url']
        elif self.doc.xpath('//iframe'):
            url = Regexp(CleanText('./@src'), '.*json_url=(.*)', default='')(self.doc.xpath('//iframe')[0])
            return unquote(url)
        return ''


class ArteJsonPage(JsonPage):

    def get_video_url(self, quality, format, version, language_version):
        _urls = Dict('videoJsonPlayer/VSR')(self.doc)
        if _urls:
            urls = _urls.keys()
            key = '_'.join([format, quality, version])
            found = self.find_url(key, urls, version, quality)
            if not found:
                # We use the default language version
                key = '_'.join([format, quality, language_version])
                found = self.find_url(key, urls, version, quality)
                if not found:
                    # We only keep the quality
                    key = '_'.join([quality, language_version])
                    found = self.find_url(key, urls, version, quality)
                    if not found:
                        found = urls[0]
            streamer = Dict('videoJsonPlayer/VSR/%s/streamer' % (found), default=None)(self.doc)
            url = Dict('videoJsonPlayer/VSR/%s/url' % (found))(self.doc)
            if streamer:
                return '%s%s' % (streamer, url), found
            return url, found
        return NotAvailable, ''

    def find_url(self, key, urls, version, quality):
        self.logger.debug('available urls: %s' % urls)
        self.logger.debug('search url matching : %s' % key)
        # Best Case: key is mathing
        matching = [s for s in urls if key in s]
        self.logger.debug('best case matching: %s' % matching)
        if matching:
            return matching[0]

        # Second Case: is the version available
        matching = [s for s in urls if version in s]
        self.logger.debug('is version available: %s' % matching)
        if matching:
            # Do the quality + version match
            matching_quality = [s for s in matching if quality in s]
            self.logger.debug('does quality + version match: %s' % matching_quality)
            if matching_quality:
                return matching[0]

            # Only format + version mathes
            return matching[0]

    @method
    class iter_videos(DictElement):
        item_xpath = 'videoList'

        class item(ArteItemElement):
            klass = ArteVideo

    @method
    class iter_programs(DictElement):
        item_xpath = 'configClusterList'

        class item(ItemElement):
            klass = Collection

            obj_title = Dict(CleanText(Env('title')))
            obj_id = Dict('clusterId')

            def obj_split_path(self):
                return [SITE.PROGRAM.get('id'), Dict('clusterId')(self)]

    @method
    class get_video(ArteItemElement):
        def __init__(self, *args, **kwargs):
            super(ArteItemElement, self).__init__(*args, **kwargs)
            self.el = self.el.get('videoJsonPlayer')

        klass = ArteVideo

    @method
    class get_arte_concert_video(ArteItemElement):
        def __init__(self, *args, **kwargs):
            super(ArteItemElement, self).__init__(*args, **kwargs)
            self.el = self.el.get('videoJsonPlayer')

        klass = ArteSiteVideo
        obj__site = SITE.CONCERT.get('id')

    @method
    class get_arte_cinema_video(ArteItemElement):
        def __init__(self, *args, **kwargs):
            super(ArteItemElement, self).__init__(*args, **kwargs)
            self.el = self.el.get('videoJsonPlayer')

        klass = ArteSiteVideo

        obj__site = SITE.CINEMA.get('id')
        obj_date = Date(Dict('VRA', default=''), default=NotAvailable)

    @method
    class get_program_video(ArteItemElement):
        def __init__(self, *args, **kwargs):
            super(ArteItemElement, self).__init__(*args, **kwargs)

            if 'videoJsonPlayer' in self.el:
                self.el = self.el.get('videoJsonPlayer')
            elif 'abstractProgram' not in self.el:
                return None
            elif 'VDO' in self.el['abstractProgram'].keys():
                self.el = self.el['abstractProgram']['VDO']

        klass = ArteVideo

    @method
    class iter_program_videos(DictElement):
        item_xpath = 'clusterWrapper/broadcasts'
        ignore_duplicate = True

        class item(ItemElement):
            klass = BaseObject

            def condition(self):
                return 'VDS' in self.el.keys() and len(self.el['VDS']) > 0

            obj_id = Dict('programId')


class SearchPage(JsonPage):
    @pagination
    @method
    class iter_videos(DictElement):
        item_xpath = 'teasers'

        class item(ItemElement):
            klass = ArteVideo

            obj_id = Dict('id')
            obj_title = Dict('title')
            obj_duration = Eval(lambda x: x * 60, Dict('duration'))
            obj_date = Date(Dict('creationDate'))

            def obj_thumbnail(self):
                try:
                    return Thumbnail(next(img['url'] for img in self.el['images'] if img['format'] == 'landscape'))
                except StopIteration:
                    return NotAvailable

        def next_page(self):
            if self.el['metas']['page'] < self.el['metas']['pages']:
                return self.page.url.rstrip('0123456789') + str(self.el['metas']['page'] + 1)

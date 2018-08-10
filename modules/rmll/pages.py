# -*- coding: utf-8 -*-

# Copyright(C) 2015 Guilhem Bonnefille
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

import re
from datetime import timedelta

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.html import CleanHTML, Link, XPath
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, DateTime, Duration, Filter, Format, Regexp
from weboob.browser.pages import HTMLPage, JsonPage
from weboob.capabilities import NotLoaded
from weboob.capabilities.collection import Collection
from weboob.capabilities.image import Thumbnail
from weboob.tools.compat import unicode

from .video import RmllVideo

BASE_URL = 'http://video.rmll.info'


class NormalizeThumbnail(Filter):
    def filter(self, thumbnail):
        if not thumbnail.startswith('http'):
            thumbnail = BASE_URL + thumbnail
        if thumbnail == "http://rmll.ubicast.tv/statics/mediaserver/images/video_icon.png":
            # This is the default: remove it as any frontend default should be better
            thumbnail = None
        return thumbnail


class RmllDuration(Duration):
    _regexp = re.compile(r'((?P<hh>\d+) h )?((?P<mm>\d+) m )?(?P<ss>\d+) s')
    kwargs = {'hours': 'hh', 'minutes': 'mm', 'seconds': 'ss'}


def create_video(metadata):
    video = RmllVideo(metadata['oid'])

    video.title = unicode(metadata['title'])
    video.date = DateTime(Dict('creation'), default=NotLoaded)(metadata)
    video.duration = RmllDuration(Dict('duration', default=''), default=NotLoaded)(metadata)
    thumbnail = NormalizeThumbnail(Dict('thumb'))(metadata)
    video.thumbnail = Thumbnail(thumbnail)
    video.thumbnail.url = video.thumbnail.id
    video.url = NotLoaded

    return video


class RmllVideoPage(HTMLPage):
    @method
    class get_video(ItemElement):
        klass = RmllVideo

        obj_id = CleanHTML('/html/head/meta[@property="og:url"]/@content') & CleanText() & Regexp(pattern=r'.*/permalink/(.+)/$')
        obj_title = Format(u'%s', CleanHTML('/html/head/meta[@name="DC.title"]/@content') & CleanText())
        obj_description = Format(u'%s', CleanHTML('/html/head/meta[@property="og:description"]/@content') & CleanText())

        def obj_thumbnail(self):
            url = NormalizeThumbnail(CleanText('/html/head/meta[@property="og:image"]/@content'))(self)
            if url:
                thumbnail = Thumbnail(url)
                thumbnail.url = thumbnail.id
                return thumbnail

        def obj_url(self):
            links = XPath('//div[@id="download_links"]/div[@class="paragraph"]/div[has-class("share")]/a[@target="_blank"]/@href')(self)
            for link in links:
                ext = str(link).split('.')[-1]
                self.logger.debug("Link:%s Ext:%s", link, ext)
                if ext in ['mp4', 'webm']:
                    return self.page.browser.BASEURL + unicode(link)


class RmllDurationPage(JsonPage):
    def get_duration(self):
        return timedelta(seconds=Dict('duration')(self.doc))


class RmllCollectionPage(HTMLPage):

    @method
    class iter_videos(ListElement):
        item_xpath = '//div[@class="item-entry type-video " or @class="item-entry type-vod "]'

        class item(ItemElement):
            klass = RmllVideo

            obj_id = Link('a') & Regexp(pattern=r'.*/videos/(.+)/$')
            obj_title = Format(u'%s', CleanHTML('a/span/span/span[@class="item-entry-title"]') & CleanText())
            obj_url = NotLoaded
            # obj_date = XPath('a/span/span/span[@class="item-entry-creation"]')

            obj_duration = CleanText('a/span/span/span[@class="item-entry-duration"]') & RmllDuration()

            def obj_thumbnail(self):
                thumbnail = NormalizeThumbnail(CleanText('a/span[@class="item-entry-preview"]/img/@src'))(self)
                if thumbnail:
                    thumbnail = Thumbnail(thumbnail)
                    thumbnail.url = thumbnail.id
                    return thumbnail


class RmllChannelsPage(JsonPage):
    def iter_resources(self, split_path):
        if 'channels' in self.doc:
            for metadata in self.doc['channels']:
                collection = Collection(split_path+[metadata['oid']], metadata['title'])
                yield collection

        if 'videos' in self.doc:
            for metadata in self.doc['videos']:
                video = create_video(metadata)
                yield video


class RmllLatestPage(JsonPage):
    def iter_resources(self):
        for metadata in self.doc['items']:
            if metadata['type'] == 'c':
                collection = Collection([metadata['oid']], metadata['title'])
                yield collection

            if metadata['type'] == 'v':
                video = create_video(metadata)
                yield video


class RmllSearchPage(JsonPage):
    def iter_resources(self):
        if 'videos' in self.doc:
            for metadata in self.doc['videos']:
                video = create_video(metadata)
                yield video

# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.filters.standard import CleanText, Regexp, Env, Duration, DateTime
from weboob.browser.filters.html import Link

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.image import Thumbnail

from weboob.exceptions import ParseError
from weboob.tools.json import json

from datetime import timedelta
import re


def determine_ext(url, default_ext='unknown_video'):
    if url is None:
        return default_ext
    guess = url.partition('?')[0].rpartition('.')[2]
    if re.match(r'^[A-Za-z0-9]+$', guess):
        return guess
    elif guess.rstrip('/') in ('mp4', 'm3u8'):
        return guess.rstrip('/')
    else:
        return default_ext


class IndexPage(HTMLPage):
    @pagination
    @method
    class iter_videos(ListElement):
        item_xpath = '//div[@data-video-id]'
        next_page = Link('//a[@title="suivant"]')

        class item(ItemElement):
            klass = BaseVideo

            def validate(self, obj):
                return obj.id

            obj_id = CleanText('./div/@data-playable')
            obj_title = CleanText('./div[@class="media-block"]/h3')
            obj_author = CleanText('./div[@class="media-block"]/div/span/a')
            obj_duration = Duration(CleanText('./div/a/div[has-class("badge--duration")]'), default=NotAvailable)

            def obj_thumbnail(self):
                url = CleanText('./div/a/img/@data-src')(self)
                thumbnail = Thumbnail(url)
                thumbnail.url = url
                return thumbnail


class VideoPage(HTMLPage):

    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_id = Env('_id')
        obj_title = CleanText('//title')
        obj_author = CleanText('//meta[@name="author"]/@content')
        obj_description = CleanText('//meta[@name="description"]/@content')

        def obj_duration(self):
            seconds = int(CleanText('//meta[@property="video:duration"]/@content', default=0)(self))
            return timedelta(seconds=seconds)

        def obj_thumbnail(self):
            url = CleanText('//meta[@property="og:image"]/@content')(self)
            thumbnail = Thumbnail(url)
            thumbnail.url = url
            return thumbnail

        obj_date = DateTime(CleanText('//meta[@property="video:release_date"]/@content'))

        def obj__formats(self):
            player = Regexp(CleanText('//script'), '.*var config = ({"context".*}}});\s*buildPlayer\(config\);.*', default=None)(self)
            if player:
                info = json.loads(player)
                if info.get('error') is not None:
                    raise ParseError(info['error']['title'])
                metadata = info.get('metadata')

                formats = {}
                for quality, media_list in metadata['qualities'].items():
                    for media in media_list:
                        media_url = media.get('url')
                        if not media_url:
                            continue
                        type_ = media.get('type')
                        if type_ == 'application/vnd.lumberjack.manifest':
                            continue
                        ext = determine_ext(media_url)
                        if ext in formats:
                            if quality in formats.get(ext):
                                formats[ext][quality] = media_url
                            else:
                                formats[ext] = {quality: media_url}
                        else:
                            formats[ext] = {quality: media_url}

                return formats
            return None

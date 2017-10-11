# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

import json
import re

from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Date, Env, Field, Format
from weboob.browser.filters.html import AbsoluteLink, Attr
from weboob.capabilities.collection import Collection
from weboob.capabilities.audio import BaseAudio, Album


class ReleasesPage(HTMLPage):
    def do_stuff(self, _id):
        raise NotImplementedError()


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_content(ListElement):
        next_page = AbsoluteLink('//a[has-class("next")]')

        class iter_albums(ListElement):
            item_xpath = '//ul[@class="result-items"]/li[.//div[@class="itemtype"][normalize-space(text())="ALBUM"]]'

            class item(ItemElement):
                klass = Album

                obj_title = CleanText('.//div[@class="heading"]/a')
                obj_url = Regexp(AbsoluteLink('.//div[@class="heading"]/a'), r'^([^?]+)\?')
                obj_id = Regexp(Field('url'), r'://([-\w]+)\.bandcamp.com/album/([-\w]+)', r'album.\1.\2', default=None)

        class iter_tracks(ListElement):
            item_xpath = '//ul[@class="result-items"]/li[.//div[@class="itemtype"][normalize-space(text())="TRACK"]]'

            class item(ItemElement):
                klass = BaseAudio

                obj_title = CleanText('.//div[@class="heading"]/a')
                obj__page_url = Regexp(AbsoluteLink('.//div[@class="heading"]/a'), r'^([^?]+)\?')
                obj_id = Regexp(Field('_page_url'), r'://([-\w]+)\.bandcamp.com/track/([-\w]+)', r'audio.\1.\2', default=None)

        class iter_artists(ListElement):
            item_xpath = '//ul[@class="result-items"]/li[.//div[@class="itemtype"][normalize-space(text())="ARTIST"]]'

            class item(ItemElement):
                klass = Collection

                obj_title = CleanText('.//div[@class="heading"]/a')
                obj_url = Regexp(AbsoluteLink('.//div[@class="heading"]/a'), r'^([^?]+)\?')
                obj_id = Regexp(Field('url'), r'://([-\w]+)\.bandcamp.com', r'artist.\1', default=None)

                def obj_split_path(self):
                    url = self.obj_url(self)
                    return [re.search(r'https://([^.]+)\.', url).group(1)]


class AlbumsPage(HTMLPage):
    def get_artist(self):
        return CleanText('//p[@id="band-name-location"]/span[@class="title"]')(self.doc)

    @method
    class iter_albums(ListElement):
        item_xpath = '//ol[has-class("music-grid")]/li'

        class item(ItemElement):
            klass = Album

            obj_url = AbsoluteLink('./a')
            obj__thumbnail_url = Attr('./a/div[@class="art"]/img', 'src')
            obj_title = CleanText('./a/p[@class="title"]', children=False)
            obj_id = Format('album.%s.%s', Env('band'), Regexp(Field('url'), r'/album/([-\w]+)'))

            def obj_author(self):
                return CleanText('./a/p[@class="title"]/span[@class="artist-override"]')(self) or self.page.get_artist()


class AlbumPage(HTMLPage):
    @method
    class get_album(ItemElement):
        klass = Album

        obj_id = Format('album.%s.%s', Env('band'), Env('album'))
        obj_title = CleanText('//h2[@class="trackTitle"]')
        obj_author = CleanText('//span[@itemprop="byArtist"]')
        _date = Date(Attr('//meta[@itemprop="datePublished"]', 'content'))

        def obj_year(self):
            return self._date(self).year

        def obj_url(self):
            return self.page.url

    @method
    class iter_tracks(ListElement):
        item_xpath= '//table[@id="track_table"]/tr[has-class("track_row_view")]'

        class item(ItemElement):
            klass = BaseAudio

            obj_title = CleanText('./td[@class="title-col"]//a')
            obj_ext = 'mp3'
            obj_format = 'mp3'
            obj_bitrate = 128
            obj__page_url = AbsoluteLink('./td[@class="title-col"]//a')
            obj_id = Format('audio.%s.%s', Env('band'), Regexp(Field('_page_url'), r'/track/([-\w]+)'))

    def get_tracks_extra(self):
        info = json.loads(re.search(r'trackinfo: (\[.+?\]),\n', self.text).group(1))
        return [{
            'url': d['file']['mp3-128'] ,
            'duration': int(d['duration']),
        } for d in info]


class TrackPage(HTMLPage):
    @method
    class get_track(ItemElement):
        klass = BaseAudio

        obj_id = Format('audio.%s.%s', Env('band'), Env('track'))
        obj_title = CleanText('//h2[@class="trackTitle"]')
        obj_author = CleanText('//span[@itemprop="byArtist"]')
        obj_ext = 'mp3'
        obj_format = 'mp3'
        obj_bitrate = 128

        def obj_duration(self):
            return int(float(Attr('//meta[@itemprop="duration"]', 'content')(self)))

        def obj_url(self):
            info = json.loads(re.search(r'trackinfo: (\[.+?\]),\n', self.page.text).group(1))
            return info[0]['file']['mp3-128']

        def obj__page_url(self):
            return self.page.url

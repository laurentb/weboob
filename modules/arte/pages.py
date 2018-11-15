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
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.collection import Collection
from weboob.capabilities.base import empty
from weboob.capabilities.video import BaseVideo
from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import DictElement, ItemElement, ListElement, method
from weboob.browser.filters.standard import Date, Env, CleanText, Field, ItemNotFound, BrowserURL
from weboob.browser.filters.json import Dict
from weboob.tools.date import parse_french_date


class ArteItemElement(ItemElement):

    def condition(self):
        return 'VID' in self.el

    obj_id = Dict('VID')
    obj_rating = Dict('VRT', default=NotAvailable)
    obj_rating_max = 10
    obj_date = Date(Dict('VDA', default=NotAvailable), default=NotAvailable)

    def obj_title(self):
        vti = Dict('VTI')(self)
        vtu = Dict('VSU', default=None)(self)
        if not vtu:
            return vti

        return '%s: %s' % (vti, vtu)

    def obj_description(self):
        try:
            return Dict('VDE')(self)
        except ItemNotFound:
            return Dict('V7T', default=NotAvailable)(self)
        except StopIteration:
            return NotAvailable

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


class ArteItemElement1(ItemElement):

    def condition(self):
        for el in Dict('stickers')(self):
            if el['code'] == "PLAYABLE":
                return True
        return False

    obj_id = Dict('programId')

    def obj_description(self):
        try:
            return Dict('fullDescription')(self)
        except ItemNotFound:
            return Dict('description')(self)
        except StopIteration:
            return NotAvailable

    def obj_title(self):
        subtitle = Dict('subtitle')(self)

        if subtitle:
            return u'{} - {}'.format(Dict('title')(self), subtitle)

        return Dict('title')(self)

    def obj_date(self):
        try:
            return Date(Dict('availability/upcomingDate'))(self)
        except ItemNotFound:
            return Date(Dict('broadcastDates/0', default=NotAvailable), default=NotAvailable)(self)
        except StopIteration:
            return NotAvailable

    def obj_duration(self):
        return timedelta(seconds=Dict('duration')(self))

    def obj_thumbnail(self):
        try:
            return Thumbnail(CleanText(Dict('images/square/resolutions/0/url'))(self))
        except ItemNotFound:
            return Thumbnail(CleanText(Dict('images/landscape/resolutions/0/url'))(self))
        except StopIteration:
            return NotAvailable


class GuidePage(HTMLPage):

    @method
    class iter_days(ListElement):
        item_xpath = r'//button/small'

        class item(ItemElement):
            klass = Collection

            obj_title = CleanText('.')

            def obj_id(self):
                return parse_french_date(CleanText('.')(self)).strftime('%Y-%m-%d')

            def obj_split_path(self):
                return Env('split_path')(self) + [u'%s' % Field('id')(self)]


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
    class iter_programs(DictElement):
        item_xpath = 'data'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Collection

            def condition(self):
                i = Dict('childrenCount')(self)
                if i is None:
                    i = 1
                return Dict('programId')(self) and i > 0

            def obj_title(self):
                subtitle = Dict('subtitle')(self)

                if subtitle:
                    return u'{} - {}'.format(Dict('title')(self), subtitle)

                return Dict('title')(self)

            obj_id = Dict('programId')

            def obj_split_path(self):
                return Env('split_path')(self) + [Dict('programId')(self)]

    @method
    class get_video(ArteItemElement):
        def __init__(self, *args, **kwargs):
            super(ArteItemElement, self).__init__(*args, **kwargs)
            self.el = self.el.get('videoJsonPlayer')

        klass = BaseVideo

    @pagination
    @method
    class iter_videos(DictElement):
        item_xpath = 'data'

        class item(ArteItemElement1):
            klass = BaseVideo

        def next_page(self):
            page = int(Env('page')(self)) + 1
            return BrowserURL('webservice',
                              page=page,
                              lang=Env('lang'),
                              method_name=Env('method_name'),
                              pattern=Env('pattern'))(self)

    @method
    class iter_guide_videos(DictElement):
        item_xpath = 'zones/1/data'

        class item(ArteItemElement1):
            klass = BaseVideo

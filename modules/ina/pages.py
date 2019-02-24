# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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

import re
from io import StringIO
import lxml.html as html

from weboob.browser.pages import JsonPage, HTMLPage, XMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method

from weboob.browser.filters.standard import CleanText, Regexp, Duration, Date, BrowserURL, Env

from weboob.capabilities.audio import BaseAudio
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.base import NotAvailable
from weboob.tools.date import DATE_TRANSLATE_FR
from weboob.tools.capabilities.audio.audio import BaseAudioIdFilter


class InaDuration(Duration):
    _regexp = re.compile(r'(?P<hh>\d+)h (?P<mm>\d+)m (?P<ss>\d+)s')


class InaDuration2(Duration):
    _regexp = re.compile(r'(?P<mm>\d+)min (?P<ss>\d+)s')
    kwargs = {'minutes': 'mm', 'seconds': 'ss'}


class InaJsonHTMLPage(JsonPage):
    ENCODING = None
    has_next = None
    scroll_cursor = None

    def __init__(self, browser, response, *args, **kwargs):
        super(InaJsonHTMLPage, self).__init__(browser, response, *args, **kwargs)
        self.encoding = self.ENCODING or response.encoding
        parser = html.HTMLParser(encoding=self.encoding)
        self.doc = html.parse(StringIO(self.doc['content']), parser)


class InaListElement(ListElement):
    item_xpath = '//div[@class="media"]'

    def next_page(self):
        first_item = Regexp(CleanText('//li[@class="suiv"]/a/@data-searchparams',
                                      default=None),
                            'b=(.*)&q=.*', default=None)
        if first_item(self):
            return BrowserURL('search_page',
                              pattern=Env('pattern'),
                              type=Env('type'),
                              first_item=first_item)(self)


class InaItemElement(ItemElement):
    obj_title = CleanText('./div[@class="media-body"]/h3/a')

    obj_description = CleanText('./div[@class="media-body"]/div/p[@class="media-body__summary"]')

    def obj_duration(self):
        duration = InaDuration(CleanText('./div[@class="media-body"]/div/span[@class="duration"]'),
                               default=None)(self)
        if duration is None:
            duration = InaDuration2(CleanText('./div[@class="media-body"]/div/span[@class="duration"]'),
                                    default=NotAvailable)(self)
        return duration

    obj_author = u'Institut National de l’Audiovisuel'
    obj_date = Date(CleanText('./div[@class="media-body"]/div/span[@class="broadcast"]'))

    def obj_thumbnail(self):
        url = CleanText('./a/img/@src')(self)
        thumbnail = Thumbnail(url)
        thumbnail.url = thumbnail.id
        return thumbnail


class InaMediaElement(ItemElement):
    obj_title = CleanText('//meta[@property="og:title"]/@content')
    obj_description = CleanText('//div[@class="notice__description"]')

    def obj_duration(self):
        duration = InaDuration(CleanText('(//div[@class="block-infos"])[1]/span[@class="duration"]'),
                               default=None)(self)
        if duration is None:
            duration = InaDuration2(CleanText('(//div[@class="block-infos"])[1]/span[@class="duration"]'),
                                    default=NotAvailable)(self)
        return duration

    obj_date = Date(CleanText('(//div[@class="block-infos"])[1]/span[@class="broadcast"]'),
                    translations=DATE_TRANSLATE_FR)
    obj_author = u'Institut National de l’Audiovisuel'

    def obj_thumbnail(self):
        url = CleanText('//meta[@property="og:image"]/@content')(self)
        thumbnail = Thumbnail(url)
        thumbnail.url = thumbnail.id
        return thumbnail


class SearchPage(InaJsonHTMLPage):
    @pagination
    @method
    class iter_audios(InaListElement):
        class item(InaItemElement):
            klass = BaseAudio

            def condition(self):
                return Regexp(CleanText('./a/@href'), '/audio/(.*)/.*.html', default=None)(self)

            obj_id = BaseAudioIdFilter(Regexp(CleanText('./a/@href'), '/audio/(.*)/.*.html'))

    @pagination
    @method
    class iter_videos(InaListElement):
        class item(InaItemElement):
            klass = BaseVideo

            def condition(self):
                return Regexp(CleanText('./a/@href'), '/video/(.*)/.*.html', default=None)(self)

            obj_id = Regexp(CleanText('./a/@href'), '/video/(.*)/.*.html')


class MediaPage(HTMLPage):
    @method
    class get_video(InaMediaElement):
        klass = BaseVideo
        obj_ext = u'mp4'
        obj_id = Env('id')

    @method
    class get_audio(InaMediaElement):
        klass = BaseAudio
        obj_ext = u'mp3'
        obj_id = BaseAudioIdFilter(Env('id'))


class RssPage(XMLPage):
    def get_media_url(self):
        url = self.doc.xpath('//media:content',
                             namespaces={'media': 'http://search.yahoo.com/mrss/'})
        return CleanText('./@url')(url[0])

# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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

import re
import hashlib

from datetime import datetime, timedelta

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.file import LICENSES
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.collection import Collection

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Format, DateTime, Duration, Date, Eval, Env, Field
from weboob.browser.filters.html import Attr, AbsoluteLink, CleanHTML
from weboob.browser.filters.json import Dict


def parse_duration(text):
    return timedelta(seconds=int(text) * 60)


class SearchPage(HTMLPage):
    @method
    class iter_videos(ListElement):
        item_xpath = '//section[h1[ends-with(text(), "vidéos")]]/ul/li'

        class item(ItemElement):
            klass = BaseVideo

            def parse(self, el):
                self.env['infos'] = CleanText('.//h3/following-sibling::p[contains(text()," min")]')(self)

                basetitle = CleanText('.//h3/a')(self)
                sub = CleanText('.//h3/following-sibling::p[1]')(self)
                if re.search(r'\d min', sub):
                    self.env['title'] = basetitle
                else:
                    self.env['title'] = '%s - %s' % (basetitle, sub)

            obj_id = AbsoluteLink('.//a')
            # obj__number = Attr('./div[@class="card-content"]//a', 'data-video-content')

            obj_title = Env('title')
            obj_thumbnail = Eval(Thumbnail, Format('https:%s', Attr('./a//img', 'data-src')))

            obj_date = Date(Regexp(Env('infos'), r'\| (\d+\.\d+\.\d+) \|',
                                   default=NotAvailable),
                            dayfirst=True, default=NotAvailable)
            obj_duration = Eval(parse_duration, Regexp(Env('infos'), r'(\d+) min'))


class VideoWebPage(HTMLPage):
    def get_number(self):
        return Attr('//div[@id="player"]', 'data-main-video')(self.doc)

    @method
    class get_video(ItemElement):
        obj_title = CleanText('//article[@id="description"]//h1')
        obj_description = CleanText('//article[@id="description"]//section/following-sibling::div')

        obj_date = DateTime(Regexp(
            CleanText('//article[@id="description"]//span[contains(text(),"diffusé le")]'),
            r'(\d{2})\.(\d{2})\.(\d{2}) à (\d{2})h(\d{2})', r'20\3/\2/\1 \4:\5'))
        obj_duration = Eval(parse_duration, Regexp(CleanText('//div[span[text()="|"]]'), r'| (\d+)min'))

        obj_thumbnail = Eval(Thumbnail, Format('https:%s', Attr('//div[@id="playerPlaceholder"]//img', 'data-src')))
        obj__number = Attr('//div[@id="player"]', 'data-main-video')
        obj_license = LICENSES.COPYRIGHT


class VideoJsonPage(JsonPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        obj_title = Format(u'%s - %s', Dict['titre'], Dict['sous_titre'])
        obj_date = Eval(datetime.fromtimestamp, Dict('diffusion/timestamp'))
        obj_duration = Dict['duree'] & Duration
        obj_description = Dict['synopsis']
        obj_ext = u'm3u8'

        obj__uuid = Dict['id']
        obj_license = LICENSES.COPYRIGHT

        def obj_url(self):
            return next((v['url_secure'] for v in self.page.doc['videos'] if v['format'] == 'm3u8-download'), None)

        obj_thumbnail = Eval(Thumbnail, Dict['image_secure'])

        def validate(self, obj):
            return obj.url


class HomePage(HTMLPage):
    @method
    class iter_categories(ListElement):
        item_xpath = '//h1'

        class item(ItemElement):
            klass = Collection

            def obj_id(self):
                id = Regexp(CleanText('./a/@href'), '//www.france.tv/(.*)/', default=None)(self)
                if not id:
                    id = CleanText('.')(self)
                    id = id.encode('ascii', 'ignore')
                    id = hashlib.md5(id).hexdigest()
                    id = u'vid_%s' % id
                return id

            obj_title = CleanText('.')

            def obj_split_path(self):
                return [Field('id')(self)]

    @method
    class iter_subcategories(ListElement):
        item_xpath = '//h2[has-class("title-wall")]'

        class item(ItemElement):
            klass = Collection

            obj_id = Regexp(CleanText('./a/@href'), '//www.france.tv/.*/(.*)/', default=None)

            obj_title = CleanText('.')

            def obj_split_path(self):
                cat = Env('cat')(self)
                cat.append(Field('id')(self))
                return cat

    @method
    class iter_videos(ListElement):
        def parse(self, el):
            self.item_xpath = self.page.item_xpath

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Format('https:%s', CleanText('./a/@href'))
            obj_title = CleanText(CleanHTML('./a/div[@class="card-content"]|./div[has-class("card-content")]'))

            def condition(self):
                return Field('title')(self)

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

from weboob.capabilities.image import BaseImage
from weboob.capabilities.video import BaseVideo

from datetime import timedelta

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Filter, CleanText, Regexp, Format, DateTime, Env, Duration
from weboob.browser.filters.html import Link, Attr, XPath
from weboob.browser.filters.json import Dict


class DurationPluzz(Filter):
    def filter(self, el):
        duration = Regexp(CleanText('.'), r'.+\|(.+)')(el[0])
        if duration[-1:] == "'":
            t = [0, int(duration[:-1])]
        else:
            t = map(int, duration.split(':'))
        return timedelta(hours=t[0], minutes=t[1])


class IndexPage(HTMLPage):

    @method
    class iter_videos(ListElement):
        item_xpath = '//div[@id="section-list_results"]/article'

        class item(ItemElement):
            klass = BaseVideo

            obj_title = Format('%s - %s', CleanText('h3/a'), CleanText('div[@class="rs-cell-details"]/a'))
            obj_id = Link('h3/a') & Regexp(pattern=r'^http://pluzz.francetv.fr/videos/.+,(.+).html$')
            obj_date = XPath('div/p[@class="diffusion"]') \
                       & CleanText(replace=[(u'à', u''), (u'  ', u' ')]) \
                       & Regexp(pattern=r'.+(\d{2}-\d{2}-\d{2}.+\d{1,2}:\d{1,2}).+') \
                       & DateTime
            obj_duration = DurationPluzz('div/span[@class="type-duree"]')

            def obj_thumbnail(self):
                url = Attr('a[@class="vignette"]/img', 'data-src')(self)
                thumbnail = BaseImage(url)
                thumbnail.url = thumbnail.id
                return thumbnail


class VideoPage(JsonPage):
    @method
    class get_video(ItemElement):
        klass = BaseVideo

        def parse(self, el):
            for video in el['videos']:
                if video['format'] != 'm3u8-download':
                    continue

                self.env['url'] = video['url']

        obj_id = Env('id')
        obj_title = Format(u'%s - %s', Dict['titre'], Dict['sous_titre'])
        obj_url = Env('url')
        obj_date = Dict['diffusion']['date_debut'] & DateTime
        obj_duration = Dict['duree'] & Duration
        obj_description = Dict['synopsis']
        obj_ext = u'm3u8'

        def obj_thumbnail(self):
            url = Format('http://pluzz.francetv.fr%s', Dict['image'])(self)
            thumbnail = BaseImage(url)
            thumbnail.url = thumbnail.id
            return thumbnail

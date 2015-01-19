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
from weboob.capabilities.base import BaseObject
from datetime import timedelta

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Filter, CleanText, Regexp, Format, DateTime, Env, Duration
from weboob.browser.filters.html import Link, Attr
from weboob.browser.filters.json import Dict


class DictElement(ListElement):
    def find_elements(self):
        if self.item_xpath is not None:
            for el in self.el.get('reponse').get(self.item_xpath):
                yield el
        else:
            yield self.el


class DurationPluzz(Filter):
    def filter(self, el):
        duration = Regexp(CleanText('.'), r'.+\|(.+)')(el[0])
        if duration[-1:] == "'":
            t = [0, int(duration[:-1])]
        else:
            t = map(int, duration.split(':'))
        return timedelta(hours=t[0], minutes=t[1])


class VideoListPage(HTMLPage):
    @method
    class get_last_video(ItemElement):
        klass = BaseVideo

        obj_id = CleanText('//div[@id="diffusion-info"]/@data-diffusion')
        obj_title = CleanText('//div[@id="diffusion-info"]/h1/div[@id="diffusion-titre"]')
        obj_date = DateTime(Regexp(CleanText('//div[@id="diffusion-info"]/div/div/span/span[1]',
                                   replace=[(u'à', u''), (u'  ', u' ')]),
                                   '.+(\d{2}-\d{2}-\d{2}.+\d{1,2}h\d{1,2}).+'),
                            dayfirst=True)

    @method
    class iter_videos(ListElement):
        item_xpath = '//div[@id="player-memeProgramme"]/a'

        class item(ItemElement):
            klass = BaseVideo

            def condition(self):
                return CleanText('div[@class="autre-emission-c3"]')(self) == "En replay"

            obj_id = Regexp(Link('.'), '^/videos/.+,(.+).html$')
            obj_title = CleanText('//meta[@name="programme_titre"]/@content')
            obj_date = DateTime(Regexp(CleanText('./div[@class="autre-emission-c2"]|./div[@class="autre-emission-c4"]',
                                                 replace=[(u'à', u''), (u'  ', u' ')]),
                                       '(\d{2}-\d{2}.+\d{1,2}:\d{1,2})'),
                                dayfirst=True)


class IndexPage(HTMLPage):

    @method
    class iter_videos(ListElement):
        item_xpath = '//div[@class="panel-resultat panel-separateur"]'

        class item(ItemElement):
            klass = BaseVideo

            obj_title = Format('%s du %s',
                               CleanText('div/div[@class="resultat-titre-diff"]/a'),
                               Regexp(CleanText('div/div[@class="resultat-soustitre-diff"]/span'),
                                      '.+(\d{2}-\d{2}-\d{2}).+'))
            obj_id = Regexp(Link('div/div[@class="resultat-titre-diff"]/a'),
                            '^/videos/.+,(.+).html$')
            obj_date = DateTime(Regexp(CleanText('div/div[@class="resultat-soustitre-diff"]/span',
                                       replace=[(u'à', u''), (u'  ', u' ')]),
                                       '.+(\d{2}-\d{2}-\d{2}.+\d{1,2}h\d{1,2}).+'))
            obj_duration = DurationPluzz('div/div[3]')

            def obj_thumbnail(self):
                url = Attr('a/img[@class="resultat-vignette"]', 'data-src')(self)
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


class Programs(JsonPage):
    @method
    class iter_programs(DictElement):
        item_xpath = 'programme'

        class item(ItemElement):
            klass = BaseObject

            obj_id = CleanText(Dict('url'))
            obj__title = CleanText(Dict('titre_programme'))


class LatestPage(JsonPage):
    @method
    class iter_videos(DictElement):
        item_xpath = 'emissions'

        class Item(ItemElement):
            klass = BaseVideo

            obj_id = Dict('id_diffusion')
            obj_title = Dict('titre_programme')
            obj_date = DateTime(Dict('date_diffusion'))

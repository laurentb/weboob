# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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

from weboob.browser.elements import ItemElement, DictElement, ListElement, method
from weboob.browser.pages import HTMLPage, JsonPage, XMLPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import XPath
from weboob.browser.filters.standard import Format, CleanText, Join, Env, Regexp, Duration, Time
from weboob.capabilities.audio import BaseAudio
from weboob.tools.capabilities.audio.audio import BaseAudioIdFilter
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.collection import Collection

import time
from datetime import timedelta, datetime, date


class PodcastPage(XMLPage):
    @method
    class iter_podcasts(ListElement):
        item_xpath = '//item'

        class item(ItemElement):
            klass = BaseAudio

            obj_id = BaseAudioIdFilter(Format('podcast.%s',
                                              Regexp(CleanText('./guid'),
                                                     'http://media.radiofrance-podcast.net/podcast09/(.*).mp3')))
            obj_title = CleanText('title')
            obj_format = u'mp3'
            obj_ext = u'mp3'

            obj_url = CleanText('enclosure/@url')
            obj_description = CleanText('description')

            def obj_author(self):
                author = self.el.xpath('itunes:author',
                                       namespaces={'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'})
                return CleanText('.')(author[0])

            def obj_duration(self):
                duration = self.el.xpath('itunes:duration',
                                         namespaces={'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'})
                return Duration(CleanText('.'))(duration[0])

            def obj_thumbnail(self):
                thumbnail = Thumbnail(CleanText('//image[1]/url')(self))
                thumbnail.url = thumbnail.id
                return thumbnail


class RadioPage(HTMLPage):
    def get_url(self):
        url = Regexp(CleanText('//script'), '.*liveUrl: \'(.*)\', timeshiftUrl.*', default=None)(self.doc)
        if not url:
            url = CleanText('//a[@id="player"][1]/@href')(self.doc)
        return url

    @method
    class get_france_culture_selection(ListElement):
        item_xpath = '//div[@id="sidebar"]/div[has-class("expression")]/div'

        class item(ItemElement):
            klass = BaseAudio

            obj_id = BaseAudioIdFilter(Format(u'%s.%s', Env('radio_id'),
                                              Regexp(CleanText('./div/div/a/@href'),
                                                     'http://media.radiofrance-podcast.net/podcast09/(.*).mp3')))
            obj_ext = u'mp3'
            obj_format = u'mp3'
            obj_url = CleanText('./div/div/a/@href')
            obj_title = Format(u'%s : %s',
                               CleanText('./a/div[@class="subtitle"]'),
                               CleanText('./a/div[@class="title"]'))
            obj_description = CleanText('./div/div/a/@data-asset-xtname')

            def obj_duration(self):
                _d = CleanText('./div/div/a/@data-duration')(self)
                return timedelta(seconds=int(_d))

    def get_france_culture_podcasts_url(self):
        for a in XPath('//a[@class="podcast"]')(self.doc):
            emission_id = Regexp(CleanText('./@href'),
                                 'http://radiofrance-podcast.net/podcast09/rss_(.*).xml', default=None)(a)
            if emission_id:
                return emission_id

    def get_france_culture_url(self):
        return CleanText('//a[@id="lecteur-commun"]/@href')(self.doc)

    @method
    class get_france_info_podcast_emissions(ListElement):
        item_xpath = '//div[@class="emission-gdp"]'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Collection

            def obj_split_path(self):
                _id = Regexp(CleanText('./div/div/div/div/ul/li/a[@class="ico-rss"]/@href'),
                             'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)
                self.env['split_path'].append(_id)
                return self.env['split_path']

            obj_id = Regexp(CleanText('./div/div/div/div/ul/li/a[@class="ico-rss"]/@href'),
                            'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')
            obj_title = CleanText('./h2/a')

    @method
    class get_mouv_podcast_emissions(ListElement):
        item_xpath = '//div[@class="view-content"]/div'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Collection

            def condition(self):
                return CleanText('./div/a[@class="podcast-rss"]/@href')(self) and \
                    Regexp(CleanText('./div/a[@class="podcast-rss"]/@href'),
                           'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)

            def obj_split_path(self):
                _id = Regexp(CleanText('./div/a[@class="podcast-rss"]/@href'),
                             'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)
                self.env['split_path'].append(_id)
                return self.env['split_path']

            obj_id = Regexp(CleanText('./div/a[@class="podcast-rss"]/@href'),
                            'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')
            obj_title = CleanText('./h2')

    @method
    class get_france_musique_podcast_emissions(ListElement):
        item_xpath = '//div[@class="liste-emissions"]/ul/li'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Collection

            def condition(self):
                return CleanText('./div/ul/li/a[@class="ico-rss"]/@href')(self) and\
                    Regexp(CleanText('./div/ul/li/a[@class="ico-rss"]/@href'),
                           'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)

            def obj_split_path(self):
                _id = Regexp(CleanText('./div/ul/li/a[@class="ico-rss"]/@href'),
                             'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)
                self.env['split_path'].append(_id)
                return self.env['split_path']

            obj_id = Regexp(CleanText('./div/ul/li/a[@class="ico-rss"]/@href'),
                            'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')
            obj_title = CleanText('./div/h3')

    @method
    class get_france_inter_podcast_emissions(ListElement):
        item_xpath = '//div[has-class("item-list")]/ul/li/div/div'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Collection

            def condition(self):
                return CleanText('./div/a[@class="podrss"]/@href')(self) and\
                    Regexp(CleanText('./div/a[@class="podrss"]/@href'),
                           'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)

            def obj_split_path(self):
                _id = Regexp(CleanText('./div/a[@class="podrss"]/@href'),
                             'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')(self)
                self.env['split_path'].append(_id)
                return self.env['split_path']

            obj_id = Regexp(CleanText('./div/a[@class="podrss"]/@href'),
                            'http://radiofrance-podcast.net/podcast09/rss_(.*).xml')
            obj_title = CleanText('./h2/a')

    def get_current(self):
        now = datetime.now()
        today = date.today()

        emission_title = u''
        for el in self.doc.xpath('//li[@class="chronique clear"]'):
            emission_time = Time(CleanText('./div[@class="quand"]',
                                           replace=[(u'à', '')]))(el)
            emission_datetime = datetime.combine(today, emission_time)
            if emission_datetime > now:
                return u'', emission_title
            emission_title = CleanText('./h3[@class="titre"]')(el)
        return u'', u''


class JsonPage(JsonPage):
    @method
    class get_france_culture_podcast_emissions(DictElement):
        class item(ItemElement):
            klass = Collection

            def obj_split_path(self):
                _id = Regexp(Dict('href'), 'emissions/(.*)')(self)
                self.env['split_path'].append(_id)
                return self.env['split_path']

            obj_id = Regexp(Dict('href'), 'emissions/(.*)')
            obj_title = Format('%s (%s)', Dict('name'), Dict('production'))

    def get_france_culture_current(self):
        for item in self.doc:
            now = int(time.time())
            for item in self.doc:
                if int(item['start']) < now and int(item['end']) > now:
                    emission = item['surtitle']
                    title = item['title']
                    if emission:
                        title = u'%s: %s' % (title, emission)
                    return u'', title
        return u'', u''

    @method
    class get_selection(DictElement):

        def __init__(self, *args, **kwargs):
            super(DictElement, self).__init__(*args, **kwargs)
            if 'json_url' not in self.env or \
               self.env['json_url'] != u'lecteur_commun_json/selection':
                self.item_xpath = 'diffusions'

        ignore_duplicate = True

        class item(ItemElement):
            klass = BaseAudio

            def condition(self):
                return Dict('path_mp3')(self)

            obj_id = BaseAudioIdFilter(Format(u'%s.%s', Env('radio_id'), Dict('nid')))
            obj_format = u'mp3'
            obj_ext = u'mp3'

            obj_title = Format(u'%s : %s',
                               Dict('title_emission'),
                               Dict('title_diff'))
            obj_description = Dict('desc_emission', default=u'')

            obj_author = Join(u', ', Dict('personnes', default=u''))
            obj_url = Dict('path_mp3')

            def obj_thumbnail(self):
                if 'path_img_emission' in self.el:
                    thumbnail = Thumbnail(Dict('path_img_emission')(self))
                    thumbnail.url = thumbnail.id
                    return thumbnail

            def obj_duration(self):
                fin = Dict('fin')(self)
                debut = Dict('debut')(self)
                if debut and fin:
                    return timedelta(seconds=int(fin) - int(debut))

    def get_current(self):
        if 'current' in self.doc:
            emission_title = self.doc['current']['emission']['titre']
            song_title = self.doc['current']['song']['titre']
            title = u'%s: %s' % (emission_title, song_title)
            person = self.doc['current']['song']['interpreteMorceau']
            return person, title
        elif 'diffusions' in self.doc:
            now = int(time.time())
            for item in self.doc['diffusions']:
                if item['debut'] < now and item['fin'] > now:
                    title = u'%s: %s' % (item['title_emission'],
                                         item['title_diff'] if 'title_diff' in item else '')
                    person = u''
                    return person, title
            return u'', u''
        else:
            now = int(time.time())
            for item in self.doc:
                if int(item['debut']) < now and int(item['fin']) > now:
                    emission = u''
                    if 'diffusions' in item and item['diffusions'] and 'title' in item['diffusions'][0]:
                        emission = item['diffusions'][0]['title']

                    title = item['title_emission']
                    if emission:
                        title = u'%s: %s' % (title, emission)

                    person = u''
                    if 'personnes' in item and item['personnes'] and item['personnes'][0]:
                        person = u','.join(item['personnes'])
                    return person, title
            return u'', u''

    def get_fburl(self):
        for el in self.doc['url']:
            if el['type'] == 'live' and el['bitrate'] == 128:
                return Dict('url')(el)

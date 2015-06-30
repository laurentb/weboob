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

from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Format, CleanText, Join, Env
from weboob.capabilities.audio import BaseAudio, BaseAudioIdFilter
from weboob.capabilities.image import BaseImage

import time
from datetime import timedelta


class PlayerPage(HTMLPage):
    def get_url(self):
        return CleanText('//a[@id="player"][1]/@href')(self.doc)


class JsonPage(JsonPage):
    @method
    class get_selection(DictElement):
        item_xpath = 'diffusions'

        class item(ItemElement):
            klass = BaseAudio

            obj_id = BaseAudioIdFilter(Format(u'%s.%s', Env('radio_id'), Dict('nid')))
            obj_format = u'mp3'
            obj_title = Format(u'%s : %s',
                               Dict('title_emission'),
                               Dict('title_diff'))
            obj_description = Dict('desc_emission', default=u'')

            obj_author = Join(u', ', Dict('personnes', default=u''))
            obj_url = Dict('path_mp3')

            def obj_thumbnail(self):
                if 'path_img_emission' in self.el:
                    thumbnail = BaseImage(Dict('path_img_emission')(self))
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
                    title = u'%s: %s' % (item['title_emission'], item['title_diff'])
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

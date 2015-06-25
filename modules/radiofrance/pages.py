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

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.filters.standard import CleanText
import time


class PlayerPage(HTMLPage):
    def get_url(self):
        return CleanText('//a[@id="player"][1]/@href')(self.doc)


class TimelinePage(JsonPage):
    def get_current(self):
        if 'current' in self.doc:
            emission_title = self.doc['current']['emission']['titre']
            song_title = self.doc['current']['song']['titre']
            title = '%s: %s' % (emission_title, song_title)
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
                if item['debut'] < now and item['fin'] > now:
                    emission = ''
                    if 'diffusions' in item and item['diffusions']:
                        emission = item['diffusions'][0]['title']

                    title = item['title_emission']
                    if emission:
                        title = u'%s: %s' % (title, emission)

                    person = u''
                    if 'personnes' in item:
                        person = u','.join(item['personnes'])
                    return person, title
            return u'', u''

# * -*- coding: utf-8 -*-

# Copyright(C) 2013  Thomas Lecavelier
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

from weboob.tools.browser import BasePage
from weboob.capabilities.radio import Radio, Stream, Emission

__all__ = ['LivePage', 'StreamsPage']

class StreamsPage(BasePage):
    def iter_radios_list(self):
        radio = Radio('necta')
        radio.title = u'Nectarine'
        radio.description = u'Nectarine Demoscene Radio'
        radio.streams = []

        index = -1

        for el in self.document.xpath('//stream'):
            index += 1
            stream_url = unicode(el.findtext('url'))
            bitrate = unicode(el.findtext('bitrate'))
            encode = unicode(el.findtext('type'))
            country = unicode(el.findtext('country')).upper()
            stream = Stream(index)
            stream.title = ' '.join([radio.title, country, encode, bitrate, 'kbps'])
            stream.url = stream_url
            radio.streams.append(stream)

        yield radio



class LivePage(BasePage):
    def get_current_emission(self):
        current = Emission(0)
        current.artist = unicode(self.document.xpath('//playlist/now/entry/artist')[0].text)
        current.title = unicode(self.document.xpath('//playlist/now/entry/song')[0].text)
        return current

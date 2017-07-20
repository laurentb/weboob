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

from weboob.browser.pages import XMLPage
from weboob.capabilities.radio import Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo


class StreamsPage(XMLPage):
    def iter_radios_list(self):
        radio = Radio('necta')
        radio.title = u'Nectarine'
        radio.description = u'Nectarine Demoscene Radio'
        radio.streams = []

        index = -1

        for el in self.doc.xpath('//stream'):
            index += 1
            stream_url = el.findtext('url')
            bitrate = el.findtext('bitrate')
            encode = el.findtext('type')
            country = el.findtext('country').upper()
            stream = BaseAudioStream(index)
            stream.bitrate = int(bitrate)
            stream.format = encode
            stream.title = ' '.join([radio.title, country, encode, str(bitrate), 'kbps'])
            stream.url = stream_url
            radio.streams.append(stream)

        yield radio


class LivePage(XMLPage):
    def get_current_emission(self):
        current = StreamInfo(0)
        current.who = self.doc.xpath('//playlist/now/entry/artist')[0].text
        current.what = self.doc.xpath('//playlist/now/entry/song')[0].text
        return current

# -*- coding: utf-8 -*-

# Copyright(C) 2013 Roger Philibert
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


from weboob.capabilities.radio import Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.browser import PagesBrowser, URL
from weboob.browser.pages import XMLPage


class SomaFMBrowser(PagesBrowser):
    QUALITIES = ['fast', 'slow', 'highest']

    BASEURL = 'http://api.somafm.com'

    infos = URL('/channels.xml', XMLPage)

    def _parse_current(self, data):
        current = data.split(' - ')
        if len(current) == 2:
            return current
        else:
            return ('Unknown', 'Unknown')

    def iter_radios(self):
        document = self.infos.go().doc
        for channel in document.iter('channel'):
            id = channel.get('id')
            radio = Radio(id)
            radio.title = channel.findtext('title')
            radio.description = channel.findtext('description')

            current_data = channel.findtext('lastPlaying')
            current = StreamInfo(0)
            current.what, current.who = self._parse_current(current_data)
            radio.current = current

            radio.streams = []
            stream_id = 0
            for subtag in channel:
                if subtag.tag.endswith('pls'):
                    stream = BaseAudioStream(stream_id)
                    bitrate = subtag.text.replace('http://somafm.com/'+id, '').replace('.pls','')
                    if bitrate != '':
                        stream.bitrate = int(bitrate)
                        bitrate += 'Kbps'
                    else:
                        stream.bitrate = 0
                        bitrate = subtag.tag.replace('pls', '')
                    stream.format = subtag.get('format')
                    stream.title = '%s/%s' % (bitrate, stream.format)
                    stream.url = subtag.text
                    radio.streams.append(stream)
                    stream_id += 1

            yield radio

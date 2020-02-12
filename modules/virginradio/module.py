# -*- coding: utf-8 -*-

# Copyright(C) 2014 Johann Broudin
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


from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection
from weboob.tools.backend import Module
from weboob.browser import Browser
from weboob.tools.misc import to_unicode


__all__ = ['VirginRadioModule']


class VirginRadioModule(Module, CapRadio, CapCollection):
    NAME = 'virginradio'
    MAINTAINER = u'Johann Broudin'
    EMAIL = 'Johann.Broudin@6-8.fr'
    VERSION = '2.1'
    DESCRIPTION = u'VirginRadio french radio'
    LICENSE = 'AGPLv3+'
    BROWSER = Browser

    _RADIOS = {
            'officiel': (
                u'Virgin Radio',
                u'Virgin Radio',
                u'http://mp3lg3.scdn.arkena.com/10490/virginradio.mp3',
                64),
            'new': (
                u'Virgin Radio New',
                u'Virgin Radio New',
                u'http://mp3lg3.tdf-cdn.com/9145/lag_103228.mp3',
                64),
            'classics': (
                u'Virgin Radio Classics',
                u'Virgin Radio Classics',
                u'http://mp3lg3.tdf-cdn.com/9146/lag_103325.mp3',
                64),
            'electroshock': (
                u'Virgin Radio Electroshock',
                u'Virgin Radio Electroshock',
                u'http://mp3lg3.tdf-cdn.com/9148/lag_103401.mp3',
                64),
            'hits': (
                u'Virgin Radio Hits',
                u'Virgin Radio Hits',
                u'http://mp3lg3.tdf-cdn.com/9150/lag_103440.mp3',
                64),
            'rock': (
                u'Virgin Radio Rock',
                u'Virgin Radio Rock',
                u'http://mp3lg3.scdn.arkena.com/9151/lag_103523.mp3',
                64)
            }

    def get_stream_info(self, radio, url):
        stream = BaseAudioStream(0)
        current = StreamInfo(0)

        r = self.browser.open(url, stream=True, headers={'Icy-Metadata':'1'})

        stream.bitrate = int(r.headers['icy-br'].split(',')[0])

        r.raw.read(int(r.headers['icy-metaint']))
        size = ord(r.raw.read(1))
        content = r.raw.read(size*16)
        r.close()

        for s in content.split("\x00")[0].split(";"):
            a = s.split("=")
            if a[0] == "StreamTitle":
                stream.title = to_unicode(a[1].split("'")[1])
                res = stream.title.split(" - ")
                current.who = to_unicode(res[0])
                if(len(res) == 1):
                    current.what = ""
                else:
                    current.what = to_unicode(res[1])

        stream.format=u'mp3'
        stream.url = url
        return [stream], current

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if radio.id not in self._RADIOS:
            return None

        title, description, url, bitrate = self._RADIOS[radio.id]

        radio.title = title
        radio.description = description

        radio.streams, radio.current = self.get_stream_info(radio.id, url)
        return radio

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            self._restrict_level(split_path)

            for id in self._RADIOS:
                yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources((Radio, ), []):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio = self.get_radio(radio.id)
        return radio

    OBJECTS = {Radio: fill_radio}

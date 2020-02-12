# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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

from __future__ import unicode_literals

from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection
from weboob.tools.backend import Module
from weboob.browser.browsers import APIBrowser


__all__ = ['NovaModule']


class NovaModule(Module, CapRadio, CapCollection):
    NAME = 'nova'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '2.0'
    DESCRIPTION = u'Nova French radio'
    LICENSE = 'AGPLv3+'
    BROWSER = APIBrowser

    RADIOS = {
        '19577': 'Radio Nova',
        '19578': 'Nova Bordeaux',
        '23678': 'Nova Lyon',
        '23929': 'Nova V.F.',
        '23932': 'Nova la Nuit',
        '23935': 'Nova Vintage',
    }

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            self._restrict_level(split_path)

            for id in self.RADIOS:
                yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources((Radio, ), []):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            if radio == 'nova': # old id
                radio = '19577'
            radio = Radio(radio)

        if radio.id not in self.RADIOS:
            return None

        json = self.browser.open('http://www.nova.fr/radio/%s/player' % radio.id).json()
        radio.title = radio.description = json['radio']['name']

        if 'currentTrack' in json:
            current = StreamInfo(0)
            current.who = json['currentTrack']['artist']
            current.what = json['currentTrack']['title']
            radio.current = current

        stream = BaseAudioStream(0)
        stream.bitrate = 128
        stream.format = 'mp3'
        stream.title = '128kbits/s'
        stream.url = json['radio']['high_def_stream_url']
        radio.streams = [stream]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            radio.current = self.get_radio(radio.id).current
        return radio

    OBJECTS = {Radio: fill_radio}

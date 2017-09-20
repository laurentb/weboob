# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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


from io import BytesIO

from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection
from weboob.tools.backend import Module
from weboob.deprecated.browser import StandardBrowser
from weboob.deprecated.browser.parsers import get_parser


__all__ = ['NovaModule']


class NovaModule(Module, CapRadio, CapCollection):
    NAME = 'nova'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'Nova French radio'
    LICENSE = 'AGPLv3+'
    BROWSER = StandardBrowser

    _RADIOS = {'nova':     (u'Radio Nova',  u'Radio nova',   u'http://broadcast.infomaniak.net:80/radionova-high.mp3'),
              }

    def create_default_browser(self):
        return self.create_browser(parser='json')

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            self._restrict_level(split_path)

            for id in self._RADIOS:
                yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources((Radio, ), []):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if radio.id not in self._RADIOS:
            return None

        title, description, url = self._RADIOS[radio.id]
        radio.title = title
        radio.description = description

        artist, title = self.get_current()
        current = StreamInfo(0)
        current.who = artist
        current.what = title
        radio.current = current

        stream = BaseAudioStream(0)
        stream.bitrate=128
        stream.format=u'mp3'
        stream.title = u'128kbits/s'
        stream.url = url
        radio.streams = [stream]
        return radio

    def get_current(self):
        doc = self.browser.location('http://www.novaplanet.com/radionova/ontheair?origin=/')
        html = doc['track']['markup']
        parser = get_parser()()
        doc = parser.parse(BytesIO(html))
        artist = u' '.join([txt.strip() for txt in doc.xpath('//div[@class="artist"]')[0].itertext()])
        title = u' '.join([txt.strip() for txt in doc.xpath('//div[@class="title"]')[0].itertext()])
        return unicode(artist).strip(), unicode(title).strip()

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = StreamInfo(0)
            radio.current.who, radio.current.what = self.get_current()
        return radio

    OBJECTS = {Radio: fill_radio}

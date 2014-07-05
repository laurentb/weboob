# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import StandardBrowser
from weboob.tools.misc import to_unicode


__all__ = ['OuiFMBackend']


class OuiFMBackend(BaseBackend, CapRadio, CapCollection):
    NAME = 'ouifm'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = u'Ouï FM French radio'
    LICENSE = 'AGPLv3+'
    BROWSER = StandardBrowser

    _RADIOS = {'general':     (u'OUÏ FM',            u'OUI FM',                       u'http://ouifm.ice.infomaniak.ch/ouifm-high.mp3', 128),
               'alternatif':  (u'OUÏ FM Alternatif', u'OUI FM - L\'Alternative Rock', u'http://ouifm.ice.infomaniak.ch/ouifm2.mp3', 128),
               'collector':   (u'OUÏ FM Collector',  u'OUI FM - Classic Rock',        u'http://ouifm.ice.infomaniak.ch/ouifm3.mp3', 160),
               'blues':       (u'OUÏ FM Blues',      u'OUI FM - Blues',               u'http://ouifm.ice.infomaniak.ch/ouifm4.mp3', 128),
               'inde':        (u'OUÏ FM Indé',       u'OUI FM - Rock Indé',           u'http://ouifm.ice.infomaniak.ch/ouifm5.mp3', 128),
              }

    def create_default_browser(self):
        return self.create_browser(parser='json')

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            self._restrict_level(split_path)

            for id in self._RADIOS.iterkeys():
                yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources((Radio, ), []):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_current(self, radio):
        document = self.browser.location('http://www.ouifm.fr/onair.json')
        rad = ''
        if radio == 'general':
            rad = 'rock'
        else:
            rad = radio

        last = document[rad][0]

        artist = to_unicode(last.get('artist', '').strip())
        title = to_unicode(last.get('title', '').strip())
        return artist, title

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if not radio.id in self._RADIOS:
            return None

        title, description, url, bitrate = self._RADIOS[radio.id]
        radio.title = title
        radio.description = description

        artist, title = self.get_current(radio.id)
        current = StreamInfo(0)
        current.who = artist
        current.what = title
        radio.current = current

        stream = BaseAudioStream(0)
        stream.bitrate=bitrate
        stream.format=u'mp3'
        stream.title = u'%skbits/s' % (stream.bitrate)
        stream.url = url
        radio.streams = [stream]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = StreamInfo(0)
            radio.current.who, radio.current.what = self.get_current(radio.id)
        return radio

    OBJECTS = {Radio: fill_radio}

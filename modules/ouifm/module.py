# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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
from weboob.tools.backend import Module
from weboob.browser.browsers import APIBrowser
from weboob.tools.misc import to_unicode


__all__ = ['OuiFMModule']


class OuiFMModule(Module, CapRadio, CapCollection):
    NAME = 'ouifm'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'OÜI FM French radio'
    LICENSE = 'AGPLv3+'
    BROWSER = APIBrowser

    _RADIOS = {'general':     (u"OÜI FM",
                               u'OÜI FM',
                               u'http://stream.ouifm.fr/ouifm-high.mp3"', 160),
               'alternatif':  (u"OÜI FM Alternatif",
                               u'OÜI FM - Alternatif',
                               u'http://alternatif.stream.ouifm.fr/ouifm2.mp3', 128),
               'classicrock': (u"OÜI FM Classic Rock",
                               u'OÜI FM - Classic Rock',
                               u'http://classicrock.stream.ouifm.fr/ouifm3.mp3', 128),
               'bluesnrock':  (u"OÜI FM Blues'n'Rock",
                               u'OÜI FM - Blues\'n\'Rock',
                               u'http://bluesnrock.stream.ouifm.fr/ouifmbluesnrock-128.mp3', 128),
               'rockinde':    (u"OÜI FM Rock Indé",
                               u'OÜI FM - Rock Indé',
                               u'http://rockinde.stream.ouifm.fr/ouifm5.mp3', 128),
               'ganja':       (u"OÜI FM Ganja",
                               u'OÜI FM - Ganja',
                               u'http://ganja.stream.ouifm.fr/ouifmganja-128.mp3', 128),
               'rock60s':     (u"OÜI FM Rock 60's",
                               u'OÜI FM - Rock 60\'s',
                               u'http://rock60s.stream.ouifm.fr/ouifmsixties.mp3', 128),
               'rock70s':     (u"OÜI FM Rock 70's",
                               u'OÜI FM - Rock 70\'s',
                               u'http://rock70s.stream.ouifm.fr/ouifmseventies.mp3', 128),
               'rock80s':     (u"OÜI FM Rock 80's",
                               u'OÜI FM - Rock 80\'s',
                               u'http://rock80s.stream.ouifm.fr/ouifmeighties.mp3', 128),
               'rock90s':     (u"OÜI FM Rock 90's",
                               u'OÜI FM - Rock 90\'s',
                               u'http://rock90s.stream.ouifm.fr/ouifmnineties.mp3', 128),
               'rock2000':    (u"OÜI FM Rock 2000",
                               u'OÜI FM - Rock 2000',
                               u'http://rock2000.stream.ouifm.fr/ouifmrock2000.mp3', 128),
               'summertime':  (u"OÜI FM Summertime",
                               u'OÜI FM - Summertime',
                               u'http://summertime.stream.ouifm.fr/ouifmsummertime.mp3', 128)}

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            self._restrict_level(split_path)

            for id in self._RADIOS:
                yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources((Radio, ), []):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_current(self, radio):
        document = self.browser.request('http://www.ouifm.fr/onair.json')
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

        if radio.id not in self._RADIOS:
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
        stream.bitrate = bitrate
        stream.format = u'mp3'
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

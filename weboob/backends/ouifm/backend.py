# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.tools.backend import BaseBackend

from .browser import OuiFMBrowser


__all__ = ['OuiFMBackend']


class OuiFMBackend(BaseBackend, ICapRadio):
    NAME = 'ouifm'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.7.1'
    DESCRIPTION = u'The Ouï FM french radio'
    LICENSE = 'GPLv3'
    BROWSER = OuiFMBrowser

    _RADIOS = {'general':     (u'OUÏ FM',            u'OUI FM',                       u'http://ouifm.ice.infomaniak.ch/ouifm-high.mp3'),
               'alternatif':  (u'OUÏ FM Alternatif', u'OUI FM - L\'Alternative Rock', u'http://ouifm.ice.infomaniak.ch/ouifm2.mp3'),
               'collector':   (u'OUÏ FM Collector',  u'OUI FM - Classic Rock',        u'http://ouifm.ice.infomaniak.ch/ouifm3.mp3'),
               'blues':       (u'OUÏ FM Blues',      u'OUI FM - Blues',               u'http://ouifm.ice.infomaniak.ch/ouifm4.mp3'),
               'inde':        (u'OUÏ FM Indé',       u'OUI FM - Rock Indé',           u'http://ouifm.ice.infomaniak.ch/ouifm5.mp3'),
              }

    def iter_radios(self):
        for id in self._RADIOS.iterkeys():
            yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_radios():
            if pattern in radio.title or pattern in radio.description:
                yield radio

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if not radio.id in self._RADIOS:
            return None

        title, description, url = self._RADIOS[radio.id]
        radio.title = title
        radio.description = description

        artist, title = self.browser.get_current(radio.id)
        current = Emission(0)
        current.artist = artist
        current.title = title
        radio.current = current

        stream = Stream(0)
        stream.title = u'128kbits/s'
        stream.url = url
        radio.streams = [stream]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = Emission(0)
            radio.current.artist, radio.current.title = self.browser.get_current(radio.id)
        return radio

    OBJECTS = {Radio: fill_radio}

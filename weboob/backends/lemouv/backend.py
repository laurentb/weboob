# * -*- coding: utf-8 -*-

# Copyright(C) 2011  Johann Broudin
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
from .browser import lemouvBrowser


__all__ = ['lemouvBackend']


class lemouvBackend(BaseBackend, ICapRadio):
    NAME = 'lemouv'
    MAINTAINER = 'Johann Broudin'
    EMAIL = 'johann.broudin@6-8.fr'
    VERSION = '1'
    DESCRIPTION = u'The le mouv\' french radio'
    LICENCE = 'GPLv3'
    BROWSER = lemouvBrowser

    _RADIOS = {'le mouv': (u'le mouv\'', u'le mouv', u'http://mp3.live.tv-radio.com/lemouv/all/lemouvhautdebit.mp3')}

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

# * -*- coding: utf-8 -*-

# Copyright(C) 2011  Johann Broudin
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


from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.capabilities.collection import ICapCollection, CollectionNotFound
from weboob.tools.backend import BaseBackend
from .browser import FranceInterBrowser


__all__ = ['FranceInterBackend']


class FranceInterBackend(BaseBackend, ICapRadio, ICapCollection):
    NAME = 'franceinter'
    MAINTAINER = 'Johann Broudin'
    EMAIL = 'johann.broudin@6-8.fr'
    VERSION = '0.8.1'
    DESCRIPTION = u'The france inter french radio'
    LICENCE = 'AGPLv3+'
    BROWSER = FranceInterBrowser

    _RADIOS = {'franceinter': (u'france inter', u'france inter', u'http://mp3.live.tv-radio.com/franceinter/all/franceinterhautdebit.mp3')}

    def iter_resources(self, splited_path):
        if len(splited_path) > 0:
            raise CollectionNotFound()

        for id in self._RADIOS.iterkeys():
            yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources([]):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if not radio.id in self._RADIOS:
            return None

        title, description, url = self._RADIOS[radio.id]
        radio.title = title
        radio.description = description

        emission = self.browser.get_current(radio.id)
        current = Emission(0)
        current.title = unicode(emission)
        current.artist = None
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
            radio.current.artist = self.browser.get_current(radio.id)
            radio.current.title = None
        return radio

    OBJECTS = {Radio: fill_radio}

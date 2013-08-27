# -*- coding: utf-8 -*-

# Copyright(C) 2013 Pierre Mazière
#
# Based on somafm backend
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
from weboob.capabilities.collection import ICapCollection
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import StandardBrowser


__all__ = ['RockRadioBackend']


class RockRadioBackend(BaseBackend, ICapRadio, ICapCollection):
    NAME = 'rockradio'
    MAINTAINER = u'Pierre Mazière'
    EMAIL = 'pierre.maziere@gmx.com'
    VERSION = '0.h'
    DESCRIPTION = u'Rock Music Internet Radio'
    LICENSE = 'AGPLv3+'
    BROWSER = StandardBrowser

    ALLINFO = 'http://www.rockradio.com'
    # FIXME
    #
    # MPlayer does not like the pls file sent from this site.

    def _parse_current(self, data):
        current = data.split(' - ')
        if len(current) == 2:
            return current
        else:
            return (u'Unknown', u'Unknown')

    def _fetch_radio_list(self):
        radios = []

        document = self.browser.location(self.ALLINFO)
        for channel in document.iter('div'):
            if ("shadow"!=channel.get('class')):
                continue
            url=u''+channel.find('a').get('href')
            radio = Radio(url[(url.rfind('/')+1):].replace('.pls',''))
            radio.title = u''+channel.getprevious().text
            radio.description = u""

            current_data = u""
            current = Emission(0)
            current.artist, current.title = self._parse_current(current_data)
            radio.current = current

            radio.streams = []
            stream_id = 0
            stream = Stream(stream_id)
            stream.title = radio.title
            stream.url = url
            radio.streams.append(stream)

            radios.append(radio)

        return radios

    def iter_radios_search(self, pattern):
        radios = self._fetch_radio_list()

        pattern = pattern.lower()
        for radio in radios:
            if pattern in radio.title.lower() or pattern in radio.description.lower():
                yield radio

    def iter_resources(self, objs, split_path):
        radios = self._fetch_radio_list()

        if Radio in objs:
            self._restrict_level(split_path)

            for radio in radios:
                yield radio

    def get_radio(self, radio_id):
        radios = self._fetch_radio_list()
        for radio in radios:
            if radio_id == radio.id:
                return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = Emission(0)
            radio.current.artist, radio.current.title = self.get_current(radio.id)
        return radio


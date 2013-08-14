# -*- coding: utf-8 -*-

# Copyright(C) 2013 Roger Philibert
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


import lxml.etree
from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.capabilities.collection import ICapCollection
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import StandardBrowser
from weboob.tools.parsers.iparser import IParser


__all__ = ['SomaFMBackend']


class LxmlParser(IParser):
    def parse(self, data, encoding=None):
        return lxml.etree.fromstring(data.read())


class SomaFMBackend(BaseBackend, ICapRadio, ICapCollection):
    NAME = 'somafm'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '0.h'
    DESCRIPTION = u'SomaFM web radio'
    LICENSE = 'AGPLv3+'
    BROWSER = StandardBrowser

    QUALITIES = ['fast', 'slow', 'highest']

    ALLINFO = 'http://api.somafm.com/channels.xml'

    def create_default_browser(self):
        return self.create_browser(parser=LxmlParser())

    def _parse_current(self, data):
        current = data.split(' - ')
        if len(current) == 2:
            return current
        else:
            return ('Unknown', 'Unknown')

    def _fetch_radio_list(self):
        radios = []

        document = self.browser.location(self.ALLINFO)
        for channel in document.iter('channel'):
            radio = Radio(channel.get('id'))
            radio.title = channel.findtext('title')
            radio.description = channel.findtext('description')

            current_data = channel.findtext('lastPlaying')
            current = Emission(0)
            current.artist, current.title = self._parse_current(current_data)
            radio.current = current

            radio.streams = []
            stream_id = 0
            for subtag in channel:
                if subtag.tag.endswith('pls'):
                    stream = Stream(stream_id)
                    stream.title = '%s/%s' % (subtag.tag.replace('pls', ''), subtag.get('format'))
                    stream.url = subtag.text
                    radio.streams.append(stream)
                    stream_id += 1

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

    #OBJECTS = {Radio: fill_radio}


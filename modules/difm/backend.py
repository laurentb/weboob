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


from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.capabilities.collection import ICapCollection
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import StandardBrowser
from weboob.tools.misc import to_unicode


__all__ = ['DIFMBackend']


class DIFMBackend(BaseBackend, ICapRadio, ICapCollection):
    NAME = 'difm'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '0.h'
    DESCRIPTION = u'Digitally Imported web radio'
    LICENSE = 'AGPLv3+'
    BROWSER = StandardBrowser

    # http://tobiass.eu/api
    # http://mpd.wikia.com/wiki/Hack:di.fm-playlists
    FORMATS = {('AAC', 64): 'public1', ('AAC', 32): 'public2', ('MP3', 96): 'public3', ('WMA', 40): 'public5'}

    def __init__(self, *a, **kw):
        super(DIFMBackend, self).__init__(*a, **kw)
        self.RADIOS = {}

    def _get_playlist_url(self, radio_key, format):
        return 'http://listen.di.fm/%s/%s.pls' % (self.FORMATS[format], radio_key)

    def _get_info_url(self, radio_key):
        self._fetch_radio_list()

        return 'http://api.audioaddict.com/v1/di/track_history/channel/%s' % self.RADIOS[radio_key]['id']

    def create_default_browser(self):
        return self.create_browser(parser='json')

    def _fetch_radio_list(self):
        if not self.RADIOS:
            document = self.browser.location('http://listen.di.fm/public3')
            for info in document:
                key = info['key']
                self.RADIOS[key] = {}
                self.RADIOS[key]['id'] = info['id']
                self.RADIOS[key]['description'] = info['description']
                self.RADIOS[key]['name'] = info['name']

        return self.RADIOS

    def iter_radios_search(self, pattern):
        self._fetch_radio_list()

        pattern = pattern.lower()
        for radio_key in self.RADIOS:
            radio_dict = self.RADIOS[radio_key]
            if pattern in radio_dict['name'].lower() or pattern in radio_dict['description'].lower():
                yield self.get_radio(radio_key)

    def iter_resources(self, objs, split_path):
        self._fetch_radio_list()

        if Radio in objs:
            self._restrict_level(split_path)

            for radio_key in self.RADIOS:
                yield self.get_radio(radio_key)

    def get_current(self, radio_key):
        document = self.browser.location(self._get_info_url(radio_key))

        artist = title = 'Advertising'
        for last in document:
            if 'ad' in last:
                continue

            artist = last.get('artist', '') or 'Unknown'
            title = last.get('title', '') or 'Unknown'

            artist = to_unicode(artist.strip())
            title = to_unicode(title.strip())
            break

        return artist, title

    def get_radio(self, radio):
        self._fetch_radio_list()

        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if not radio.id in self.RADIOS:
            return None

        radio_dict = self.RADIOS[radio.id]
        radio.title = radio_dict['name']
        radio.description = radio_dict['description']

        artist, title = self.get_current(radio.id)
        current = Emission(0)
        current.artist = artist
        current.title = title
        radio.current = current

        radio.streams = []
        for stream_id, format in enumerate(self.FORMATS):
            stream = Stream(stream_id)
            stream.title = u'%s %skbps' % format
            stream.url = self._get_playlist_url(radio.id, format)
            radio.streams.append(stream)
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = Emission(0)
            radio.current.artist, radio.current.title = self.get_current(radio.id)
        return radio

    OBJECTS = {Radio: fill_radio}


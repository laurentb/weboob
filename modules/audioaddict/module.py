# -*- coding: utf-8 -*-

# Copyright(C) 2013 Pierre Mazière
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

from __future__ import unicode_literals

from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection, Collection
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.browser.browsers import APIBrowser
import time

__all__ = ['AudioAddictModule']


#
# WARNING
#
# AudioAddict playlists do not seem to be appreciated by mplayer
# VLC plays them successfully, therefore I advice to set the media_player
# option to another player in the ~/.config/weboob/radioob config file:
# [ROOT]
# media_player = your_non_mplayer_player
class AudioAddictModule(Module, CapRadio, CapCollection):
    NAME = 'audioaddict'
    MAINTAINER = u'Pierre Mazière'
    EMAIL = 'pierre.maziere@gmx.com'
    VERSION = '1.5'
    DESCRIPTION = u'Internet radios powered by audioaddict.com services'
    LICENSE = 'AGPLv3+'
    BROWSER = APIBrowser

    # Data extracted from http://tobiass.eu/api-doc.html
    NETWORKS = {
        'DI': {
            'desc': 'Digitally Imported addictive electronic music',
            'domain': 'listen.di.fm',
            'streams': {  # 'android_low': {'rate': 40, 'fmt': 'aac'},
                        # 'android': {'rate': 64, 'fmt': 'aac'},
                        # 'android_high': {'rate': 96, 'fmt': 'aac'},
                        'android_premium_low': {'rate': 40, 'fmt': 'aac'},
                        'android_premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'android_premium': {'rate': 128, 'fmt': 'aac'},
                        'android_premium_high': {'rate': 256, 'fmt': 'aac'},
                        # 'public1': {'rate': 64, 'fmt': 'aac'},
                        # 'public2': {'rate': 40, 'fmt': 'aac'},
                        # 'public3': {'rate': 96, 'fmt': 'mp3'},
                        'premium_low': {'rate': 40, 'fmt': 'aac'},
                        'premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'premium': {'rate': 128, 'fmt': 'aac'},
                        'premium_high': {'rate': 256, 'fmt': 'mp3'}
                        }
        },
        'RadioTunes': {
            'desc': 'Radio Tunes',
            'domain': 'listen.radiotunes.com',
            'streams': {  # 'appleapp_low': {'rate': 40, 'fmt': 'aac'},
                        # 'appleapp': {'rate': 64, 'fmt': 'aac'},
                        'appleapp_high': {'rate': 96, 'fmt': 'mp3'},
                        'appleapp_premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'appleapp_premium': {'rate': 128, 'fmt': 'aac'},
                        'appleapp_premium_high': {'rate': 256, 'fmt': 'mp3'},
                        # 'public1': {'rate': 40, 'fmt': 'aac'},
                        # 'public5': {'rate': 40, 'fmt': 'wma'},
                        # 'public3': {'rate': 96, 'fmt': 'mp3'},
                        'premium_low': {'rate': 40, 'fmt': 'aac'},
                        'premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'premium': {'rate': 128, 'fmt': 'aac'},
                        'premium_high': {'rate': 256, 'fmt': 'mp3'}
                        }
        },
        'JazzRadio': {
            'desc': 'Jazz Radio',
            'domain': 'listen.jazzradio.com',
            'streams': {  # 'appleapp_low': {'rate': 40, 'fmt': 'aac'},
                        # 'appleapp': {'rate': 64, 'fmt': 'aac'},
                        'appleapp_premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'appleapp_premium': {'rate': 128, 'fmt': 'aac'},
                        'appleapp_premium_high': {'rate': 256, 'fmt': 'mp3'},
                        # 'public1': {'rate': 40, 'fmt': 'aac'},
                        # 'public3': {'rate': 64, 'fmt': 'mp3'},
                        'premium_low': {'rate': 40, 'fmt': 'aac'},
                        'premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'premium': {'rate': 128, 'fmt': 'aac'},
                        'premium_high': {'rate': 256, 'fmt': 'mp3'}
                        }
        },
        'RockRadio': {
            'desc': 'Rock Radio',
            'domain': 'listen.rockradio.com',
            'streams': {  # 'android_low': {'rate': 40, 'fmt': 'aac'},
                        # 'android': {'rate': 64, 'fmt': 'aac'},
                        'android_premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'android_premium': {'rate': 128, 'fmt': 'aac'},
                        'android_premium_high': {'rate': 256, 'fmt': 'mp3'},
                        # 'public1': {'rate': 96, 'fmt': 'mp3'}
                        }
        },
        'ClassicalRadio': {
            'desc': 'Classical Radio',
            'domain': 'listen.classicalradio.com',
            'streams': {  # 'android_low': {'rate': 40, 'fmt': 'aac'},
                        # 'android': {'rate': 64, 'fmt': 'aac'},
                        'android_premium_medium': {'rate': 64, 'fmt': 'aac'},
                        'android_premium': {'rate': 128, 'fmt': 'aac'},
                        'android_premium_high': {'rate': 256, 'fmt': 'mp3'},
                        # 'public1': {'rate': 96, 'fmt': 'mp3'}
                        }
        },
    }

    CONFIG = BackendConfig(Value('networks',
                                 label='Selected Networks [%s](space separated)' %
                                 ' '.join(NETWORKS.keys()), default=''),
                           Value('quality', label='Radio streaming quality',
                                 choices={'h': 'high', 'l': 'low'},
                                 default='h')
                           )

    def __init__(self, *a, **kw):
        super(AudioAddictModule, self).__init__(*a, **kw)
        if 'FrescaRadio' in self.config['networks'].get():
            raise self.ConfigError('FresacaRadio does not exists anymore')
        self.RADIOS = {}
        self.HISTORY = {}

    def _get_tracks_history(self, network):
        self._fetch_radio_list(network)
        domain = self.NETWORKS[network]['domain']
        url = 'http://api.audioaddict.com/v1/%s/track_history' %\
              (domain[domain.find('.') + 1:domain.rfind('.')])
        self.HISTORY[network] = self.browser.request(url)
        return self.HISTORY

    def create_default_browser(self):
        return self.create_browser()

    def _get_stream_name(self, network, quality):
        streamName = 'public3'
        for name in self.NETWORKS[network]['streams'].keys():
            if name.startswith('public') and \
               self.NETWORKS[network]['streams'][name]['rate'] >= 64:
                if quality == 'h':
                    streamName = name
                    break
            else:
                if quality == 'l':
                    streamName = name
                    break
        return streamName

    def _fetch_radio_list(self, network=None):
        quality = self.config['quality'].get()
        for selectedNetwork in self.config['networks'].get().split():
            if network is None or network == selectedNetwork:
                streamName = self._get_stream_name(selectedNetwork, quality)
                if not self.RADIOS:
                    self.RADIOS = {}
                if selectedNetwork not in self.RADIOS:
                    document = self.browser.request('http://%s/%s' %
                                                    (self.NETWORKS[selectedNetwork]['domain'],
                                                     streamName))
                    self.RADIOS[selectedNetwork] = {}
                    for info in document:
                        radio = info['key']
                        self.RADIOS[selectedNetwork][radio] = {}
                        self.RADIOS[selectedNetwork][radio]['id'] = info['id']
                        self.RADIOS[selectedNetwork][radio]['name'] = info['name']
                        self.RADIOS[selectedNetwork][radio]['playlist'] = info['playlist']

        return self.RADIOS

    def iter_radios_search(self, pattern):
        self._fetch_radio_list()

        pattern = pattern.lower()
        for network in self.config['networks'].get().split():
            for radio in self.RADIOS[network]:
                radio_dict = self.RADIOS[network][radio]
                if pattern in radio_dict['name'].lower():
                    yield self.get_radio(radio+"."+network)

    def iter_resources(self, objs, split_path):
        self._fetch_radio_list()

        if Radio in objs:
            for network in self.config['networks'].get().split():
                if split_path == [network]:
                    for radio in self.RADIOS[network]:
                        yield self.get_radio(radio+"."+network)
                    return
            for network in self.config['networks'].get().split():
                yield Collection([network], self.NETWORKS[network]['desc'])

    def get_current(self, network, radio):
        channel = {}
        if network not in self.HISTORY:
            self._get_tracks_history(network)
            channel = self.HISTORY[network].get(str(self.RADIOS[network][radio]['id']))
        else:
            now = time.time()
            channel = self.HISTORY[network].get(str(self.RADIOS[network][radio]['id']))
            if channel is None:
                return 'Unknown', 'Unknown'
            if (channel.get('started') + channel.get('duration')) < now:
                self._get_tracks_history(network)
                channel = self.HISTORY[network].get(str(self.RADIOS[network][radio]['id']))

        artist = u'' + (channel.get('artist', '') or 'Unknown')
        title = u''+(channel.get('title', '') or 'Unknown')

        if artist == 'Unknown':
            track = u'' + (channel.get('track', '') or 'Unknown')
            if track != 'Unknown':
                artist = track[:track.find(' - ')]

        return artist, title

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        radioName, network = radio.id.split('.', 1)

        self._fetch_radio_list(network)

        if radioName not in self.RADIOS[network]:
            return None

        radio_dict = self.RADIOS[network][radioName]
        radio.title = radio_dict['name']
        radio.description = radio_dict['name']

        artist, title = self.get_current(network, radioName)
        current = StreamInfo(0)
        current.who = artist
        current.what = title
        radio.current = current

        radio.streams = []
        defaultname = self._get_stream_name(network, self.config['quality'].get())
        stream = BaseAudioStream(0)
        stream.bitrate = self.NETWORKS[network]['streams'][defaultname]['rate']
        stream.format = self.NETWORKS[network]['streams'][defaultname]['fmt']
        stream.title = u'%s %skbps' % (stream.format, stream.bitrate)
        stream.url = 'http://%s/%s/%s.pls' %\
                     (self.NETWORKS[network]['domain'], defaultname, radioName)
        radio.streams.append(stream)
        i = 1
        for name in self.NETWORKS[network]['streams'].keys():
            if name == defaultname:
                continue
            stream = BaseAudioStream(i)
            stream.bitrate = self.NETWORKS[network]['streams'][name]['rate']
            stream.format = self.NETWORKS[network]['streams'][name]['fmt']
            stream.title = u'%s %skbps' % (stream.format, stream.bitrate)
            stream.url = 'http://%s/%s/%s.pls' % \
                         (self.NETWORKS[network]['domain'], name, radioName)

            radio.streams.append(stream)
            i = i + 1
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            radioName, network = radio.id.split('.', 1)
            radio.current = StreamInfo(0)
            radio.current.who, radio.current.what = self.get_current(network, radioName)
            return radio

    OBJECTS = {Radio: fill_radio}

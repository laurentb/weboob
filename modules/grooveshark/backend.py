# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.capabilities.audio import ICapAudio, BaseAudio
from weboob.capabilities.collection import ICapCollection, Collection, CollectionNotFound
from .browser import GroovesharkBrowser
from weboob.tools.value import ValueBackendPassword, Value

__all__ = ['GroovesharkBackend']


class GroovesharkBackend(BaseBackend, ICapAudio, ICapCollection):
    NAME = 'grooveshark'
    DESCRIPTION = u'Grooveshark music streaming website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.j'
    LICENSE = 'AGPLv3+'

    BROWSER = GroovesharkBrowser
    CONFIG = BackendConfig(Value('username', label='Login', default=''),
                           ValueBackendPassword('password', label='Password', default=''))

    def create_default_browser(self):
        password = None
        username = self.config['username'].get()
        if len(username) > 0:
            password = self.config['password'].get()
        return self.create_browser(username, password)

    def fill_audio(self, audio, fields):
        if 'url' in fields:
            with self.browser:
                audio.url = unicode(self.browser.get_stream_url_from_song_id(audio.id))
        if 'thumbnail' in fields and audio.thumbnail:
            with self.browser:
                audio.thumbnail.data = self.browser.readurl(audio.thumbnail.url)

    def search_audio(self, pattern, sortby=ICapAudio.SEARCH_RELEVANCE):
        with self.browser:
            return self.browser.search_audio(pattern)

    def get_audio(self, _id):
        with self.browser:
            return self.browser.get_audio_from_song_id(_id)

    def iter_resources(self, objs, split_path):
        with self.browser:
            if BaseAudio in objs:
                collection = self.get_collection(objs, split_path)
                if collection.path_level == 0:
                    yield Collection([u'albums'], u'Search for Albums')
                    if self.browser.is_logged():
                        yield Collection([u'playlists'], u'Grooveshark Playlists')
                if collection.path_level == 1:
                    if collection.split_path[0] == u'playlists':
                        for item in self.browser.get_all_user_playlists(collection.split_path):
                            yield item
                    elif collection.split_path[0] == u'albums':
                        print u'Enter cd [%s\'s name] then ls to launch search' % collection.split_path[0]
                if collection.path_level == 2:
                    if collection.split_path[0] == u'albums':
                        for item in self.browser.search_albums(collection.split_path):
                            yield item
                    if collection.split_path[0] == u'playlists':
                        for audio in self.browser.get_all_songs_from_playlist(collection.split_path[1]):
                            yield audio
                if collection.path_level == 3 and collection.split_path[0] == u'albums':
                    for audio in self.browser.get_all_songs_from_album(collection.split_path[2]):
                        yield audio

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return

        if BaseAudio in objs and (collection.split_path == [u'albums'] or collection.split_path == [u'playlists']):
            return

        if BaseAudio in objs and collection.path_level == 2 and \
                (collection.split_path[0] == u'albums' or collection.split_path[0] == u'playlists'):
            if collection.split_path[0] == u'playlists':
                try:
                    int(collection.split_path[1])
                except ValueError:
                    raise CollectionNotFound(collection.split_path)

            return

        if BaseAudio in objs and collection.path_level == 3 and \
                (collection.split_path[0] == u'albums'):
            try:
                int(collection.split_path[2])
            except ValueError:
                raise CollectionNotFound(collection.split_path)
            return

        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseAudio: fill_audio}

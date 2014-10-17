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


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.audio import CapAudio, BaseAudio, Album, Playlist, decode_id
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from .browser import GroovesharkBrowser
from weboob.tools.value import ValueBackendPassword, Value

__all__ = ['GroovesharkModule']


def cmp_id(p1, p2):
    if p1.id == p2.id:
        return 0
    if p1.id > p2.id:
        return 1
    return -1


class GroovesharkModule(Module, CapAudio, CapCollection):
    NAME = 'grooveshark'
    DESCRIPTION = u'Grooveshark music streaming website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '1.1'
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
                _id = BaseAudio.decode_id(audio.id)
                audio.url = unicode(self.browser.get_stream_url_from_song_id(_id))
        if 'thumbnail' in fields and audio.thumbnail:
            with self.browser:
                audio.thumbnail.data = self.browser.readurl(audio.thumbnail.url)

    def search_audio(self, pattern, sortby=CapAudio.SEARCH_RELEVANCE):
        with self.browser:
            return self.browser.search_audio(pattern)

    @decode_id(BaseAudio.decode_id)
    def get_audio(self, _id):
        with self.browser:
            return self.browser.get_audio_from_song_id(_id)

    def fill_album(self, album, fields):
        _id = Album.decode_id(album.id)
        album.tracks_list = []
        for song in self.browser.get_all_songs_from_album(_id):
            album.tracks_list.append(song)

    def search_album(self, pattern, sortby=CapAudio.SEARCH_RELEVANCE):
        with self.browser:
            return self.browser.search_albums(pattern)

    @decode_id(Album.decode_id)
    def get_album(self, _id):
        with self.browser:
            album = self.browser.get_album_by_id(_id)
            album.tracks_list = []
            for song in self.browser.get_all_songs_from_album(_id):
                album.tracks_list.append(song)

            album.tracks_list.sort(cmp=cmp_id)
            return album

    def fill_playlist(self, playlist, fields):
        playlist.tracks_list = []
        _id = Playlist.decode_id(playlist.id)
        for song in self.browser.get_all_songs_from_playlist(_id):
            playlist.tracks_list.append(song)

    def search_playlist(self, pattern, sortby=CapAudio.SEARCH_RELEVANCE):
        with self.browser:
            lower_pattern = pattern.lower()
            for playlist in self.browser.get_all_user_playlists():
                if lower_pattern in playlist.title.lower():
                    yield playlist

    @decode_id(Playlist.decode_id)
    def get_playlist(self, _id):
        with self.browser:
            playlist = Playlist(_id)
            playlist.tracks_list = []
            for song in self.browser.get_all_songs_from_playlist(_id):
                playlist.tracks_list.append(song)

            return playlist

    def iter_resources(self, objs, split_path):
        with self.browser:
            if len(split_path)  == 0:
                if Playlist in objs:
                    self._restrict_level(split_path)
                if self.browser.is_logged():
                    for item in self.browser.get_all_user_playlists():
                        yield item

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return

        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseAudio: fill_audio, Album: fill_album, Playlist: fill_playlist}

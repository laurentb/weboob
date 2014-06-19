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

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.tools.json import json as simplejson
from weboob.capabilities.audio import BaseAudio, Album, Playlist
from weboob.capabilities.image import BaseImage
from weboob.capabilities import NotAvailable

import hashlib
import uuid
import string
import random
import datetime

__all__ = ['GroovesharkBrowser']


class GroovesharkAudio(BaseAudio):
    def __init__(self, *args, **kwargs):
        BaseAudio.__init__(self, *args, **kwargs)
        self.ext = u'mp3'


class APIError(Exception):
    pass


class GroovesharkBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'html5.grooveshark.com'
    API_URL = 'https://html5.grooveshark.com/more.php'

    #Setting the static header (country, session and uuid)
    HEADER = {}
    HEADER['country'] = {}
    HEADER['country']['CC1'] = 0
    HEADER['country']['CC2'] = 0
    HEADER['country']['CC3'] = 0
    HEADER['country']['CC4'] = 0
    HEADER['country']['ID'] = 1
    HEADER['country']['IPR'] = 1
    HEADER['privacy'] = 0
    HEADER['session'] = (''.join(random.choice(string.digits + string.letters[:6]) for x in range(32))).lower()
    HEADER["uuid"] = str.upper(str(uuid.uuid4()))

    #those values depends on a grooveshark version and may change
    GROOVESHARK_CONSTANTS = ('mobileshark', '20120830', 'gooeyFlubber')
    COMMUNICATION_TOKEN = None

    user_id = None

    def home(self):
        self.login()
        self.get_communication_token()

    def is_logged(self):
        return self.user_id is not None and self.user_id != 0

    def login(self):
        if self.username and self.password:
            method = 'authenticateUser'

            parameters = {}
            parameters['username'] = self.username
            parameters['password'] = self.password

            response = self.API_post(method, parameters, self.create_token(method))
            self.user_id = response['result']['userID']

            if not self.is_logged:
                raise BrowserIncorrectPassword()

    def get_all_user_playlists(self):
        if self.is_logged():
            method = 'userGetPlaylists'
            parameters = {}
            parameters['userID'] = self.user_id
            response = self.API_post(method, parameters, self.create_token(method))
            return self.create_playlists_from_result(response['result']['Playlists'])
        return []

    def create_search_parameter(self, _type, pattern):
        parameters = {}
        parameters['query'] = pattern.encode(self.ENCODING)
        parameters['type'] = [_type]
        parameters['guts'] = 0
        parameters['ppOverr'] = ''
        return parameters

    def search_audio(self, pattern):
        method = 'getResultsFromSearch'
        response = self.API_post(method, self.create_search_parameter('Songs', pattern), self.create_token(method))
        return self.create_audio_from_songs_result(response['result']['result']['Songs'])

    def create_audio_from_songs_result(self, songs):
        for song in songs:
            yield self.create_audio(song)

    def get_audio_from_song_id(self, _id):
        audio = GroovesharkAudio(_id)
        audio.url = self.get_stream_url_from_song_id(_id)
        if audio.url is not None:
            return audio
        else:
            return None

    def get_stream_url_from_song_id(self, _id):
        method = 'getStreamKeyFromSongIDEx'
        try:
            parameters = {}
            parameters['prefetch'] = False
            parameters['mobile'] = True
            parameters['songID'] = int(_id)
            parameters['country'] = self.HEADER['country']

            response = self.API_post(method, parameters, self.create_token(method))

            self.mark_song_downloaded_ex(response['result'])

            return u'http://%s/stream.php?streamKey=%s' % (response['result']['ip'], response['result']['streamKey'])
        except ValueError:
            return

    def search_albums(self, pattern):
        method = 'getResultsFromSearch'
        response = self.API_post(method, self.create_search_parameter('Albums', pattern), self.create_token(method))
        return self.create_albums_from_result(response['result']['result']['Albums'])

    def get_album_by_id(self, _id):
        method = 'getAlbumByID'
        parameters = {}
        parameters['albumID'] = _id
        response = self.API_post(method, parameters, self.create_token(method))
        return self.create_album(response['result'])

    def create_albums_from_result(self, albums):
        for _album in albums:
            yield self.create_album(_album)

    def create_album(self, _album):
        album = Album(_album['AlbumID'])
        try:
            album.title = u'%s' % _album['AlbumName']
        except:
            album.title = u'%s' % _album['Name']

        album.author = u'%s' % _album['ArtistName']
        album.year = int(_album['Year'])
        if _album['CoverArtFilename']:
            album.thumbnail = BaseImage(u'http://images.gs-cdn.net/static/albums/80_' + _album['CoverArtFilename'])
            album.thumbnail.url = album.thumbnail.id
        return album

    def get_all_songs_from_album(self, album_id):
        method = 'albumGetAllSongs'

        parameters = {}
        parameters['prefetch'] = False
        parameters['mobile'] = True
        parameters['albumID'] = int(album_id)
        parameters['country'] = self.HEADER['country']

        response = self.API_post(method, parameters, self.create_token(method))
        return self.create_audio_from_album_result(response['result'])

    def create_audio_from_album_result(self, songs):
        for song in songs:
            audio = self.create_audio(song)
            if audio:
                yield audio

    def create_audio(self, song):
        audio = GroovesharkAudio(song['SongID'])
        try:
            audio.title = u'%s' % song['SongName'].encode('ascii', 'replace')
        except:
            audio.title = u'%s' % song['Name'].encode('ascii', 'replace')

        audio.author = u'%s' % song['ArtistName'].encode('ascii', 'replace')
        audio.description = u'%s - %s' % (audio.author, song['AlbumName'].encode('ascii', 'replace'))

        if song['CoverArtFilename']:
            audio.thumbnail = BaseImage(u'http://images.gs-cdn.net/static/albums/40_' + song['CoverArtFilename'])
            audio.thumbnail.url = audio.thumbnail.id

        if song['EstimateDuration']:
            audio.duration = datetime.timedelta(seconds=int(float(song['EstimateDuration'])))

        try:
            if 'Year' in song.keys() and song['Year']:
                audio.date = datetime.date(year=int(song['Year']), month=1, day=1)
        except ValueError:
            audio.date = NotAvailable

        return audio

    def create_playlists_from_result(self, playlists):
        for _playlist in playlists:
            playlist = Playlist(_playlist['PlaylistID'])
            playlist.title = u'%s' % (_playlist['Name'])
            yield playlist

    def get_all_songs_from_playlist(self, playlistID):
        method = 'getPlaylistByID'

        parameters = {}
        parameters['playlistID'] = playlistID

        response = self.API_post(method, parameters, self.create_token(method))
        return self.create_audio_from_album_result(response['result']['Songs'])

    def get_communication_token(self):
        parameters = {'secretKey': hashlib.md5(self.HEADER["session"]).hexdigest()}
        result = self.API_post('getCommunicationToken', parameters)
        self.COMMUNICATION_TOKEN = result['result']

    def create_token(self, method):
        if self.COMMUNICATION_TOKEN is None:
            self.get_communication_token()

        rnd = (''.join(random.choice(string.hexdigits) for x in range(6)))
        return rnd + hashlib.sha1('%s:%s:%s:%s' % (method,
                                                   self.COMMUNICATION_TOKEN,
                                                   self.GROOVESHARK_CONSTANTS[2],
                                                   rnd)).hexdigest()

    # in order to simulate a real browser
    def mark_song_downloaded_ex(self, response):
        method = 'markSongDownloadedEx'

        parameters = {}
        parameters['streamKey'] = response['streamKey']
        parameters['streamServerID'] = response['streamServerID']
        parameters['songID'] = response['SongID']

        response = self.API_post(method, parameters, self.create_token(method))

    def check_result(self, result):
        if 'fault' in result:
            raise APIError('%s' % result['fault']['message'])
        if not result['result']:
            raise APIError('%s' % "No response found")

    def API_post(self, method, parameters, token=None):
        """
        Submit a POST request to the website
        The JSON data is parsed and returned as a dictionary
        """
        data = self.create_json_data(method, parameters, token)
        req = self.create_request(method)
        response = self.openurl(req, data)
        return self.parse_response(response)

    def create_json_data(self, method, parameters, token):
        data = {}
        data['header'] = self.HEADER
        data['header']['client'] = self.GROOVESHARK_CONSTANTS[0]
        data['header']['clientRevision'] = self.GROOVESHARK_CONSTANTS[1]
        if(token is not None):
            data['header']['token'] = token
        data['method'] = method
        data['parameters'] = parameters
        return simplejson.dumps(data)

    def create_request(self, method):
        req = self.request_class('%s?%s' % (self.API_URL, method))
        req.add_header('Content-Type', 'application/json')
        return req

    def parse_response(self, response):
        result = simplejson.loads(response.read(), self.ENCODING)
        self.check_result(result)
        return result

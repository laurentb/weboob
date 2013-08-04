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

from weboob.tools.browser import BaseBrowser
from weboob.tools.json import json as simplejson
from weboob.capabilities.video import BaseVideo
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.thumbnail import Thumbnail
import hashlib
import uuid
import string
import random
import datetime

__all__ = ['GroovesharkBrowser']


class GroovesharkVideo(BaseVideo):
    def __init__(self, *args, **kwargs):
        BaseVideo.__init__(self, *args, **kwargs)
        self.ext = u'mp3'


class APIError(Exception):
    pass


class GroovesharkBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'html5.grooveshark.com'
    #SAVE_RESPONSE = True
    #DEBUG_HTTP = True
    #DEBUG_MECHANIZE = True
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

    VIDEOS_FROM_SONG_RESULTS = None

    def home(self):
        self.get_communication_token()

    def search_videos(self, pattern):
        method = 'getResultsFromSearch'

        parameters = {}
        parameters['query'] = pattern.encode(self.ENCODING)
        parameters['type'] = ['Songs']  # ['Songs','Playlists','Albums']
        parameters['guts'] = 0
        parameters['ppOverr'] = ''

        response = self.API_post(method, parameters, self.create_token(method))

        songs = self.create_video_from_songs_result(response['result']['result']['Songs'])
        #playlists = self.create_video_from_playlist_result(response['result']['result']['Playlists'])
        #albums = self.create_video_from_albums_result(response['result']['result']['Albums'])

        return songs

    def create_video_from_songs_result(self, songs):
        self.VIDEOS_FROM_SONG_RESULTS = []

        for song in songs:
            video = GroovesharkVideo(song['SongID'])
            video.title = u'Song - %s' % song['SongName'].encode('ascii', 'replace')
            video.author = u'%s' % song['ArtistName'].encode('ascii', 'replace')
            video.description = u'%s - %s - %s' % (video.author, song['AlbumName'].encode('ascii', 'replace'), song['Year'].encode('ascii', 'replace'))
            video.thumbnail = Thumbnail(u'http://images.gs-cdn.net/static/albums/40_' + song['CoverArtFilename'])
            video.duration = datetime.timedelta(seconds=int(float(song['EstimateDuration'])))
            video.rating = float(song['AvgRating'])
            try:
                video.date = datetime.date(year=int(song['Year']), month=1, day=1)
            except ValueError:
                video.date = NotAvailable
            self.VIDEOS_FROM_SONG_RESULTS.append(video)

            yield video

    def create_video_from_playlist_result(self, playlists):
        videos = []
        for playlist in playlists:
            video = GroovesharkVideo(playlist['PlaylistID'])
            video.title = u'Playlist - %s' % (playlist['Name'])
            video.description = playlist['Artists']
            videos.append(video)
        return videos

    def create_video_from_albums_result(self, albums):
        videos = []
        for album in albums:
            video = GroovesharkVideo(album['AlbumID'])
            video.title = u'Album - %s' % (album['Name'])
            video.description = album['Year']
            videos.append(video)
        return videos

    def get_communication_token(self):
        parameters = {'secretKey': hashlib.md5(self.HEADER["session"]).hexdigest()}
        result = self.API_post('getCommunicationToken', parameters)
        self.COMMUNICATION_TOKEN = result['result']

    def create_token(self, method):
        if self.COMMUNICATION_TOKEN is None:
            self.get_communication_token()

        rnd = (''.join(random.choice(string.hexdigits) for x in range(6)))
        return rnd + hashlib.sha1('%s:%s:%s:%s' % (method, self.COMMUNICATION_TOKEN, self.GROOVESHARK_CONSTANTS[2], rnd)).hexdigest()

    def get_video_from_song_id(self, song_id):
        if self.VIDEOS_FROM_SONG_RESULTS:
            for video in self.VIDEOS_FROM_SONG_RESULTS:
                if video.id == song_id:
                    video.url = self.get_stream_url_from_song_id(song_id)
                    return video

    def get_stream_url_from_song_id(self, song_id):
        method = 'getStreamKeyFromSongIDEx'

        parameters = {}
        parameters['prefetch'] = False
        parameters['mobile'] = True
        parameters['songID'] = int(song_id)
        parameters['country'] = self.HEADER['country']

        response = self.API_post(method, parameters, self.create_token(method))

        self.mark_song_downloaded_ex(response['result'])

        return u'http://%s/stream.php?streamKey=%s' % (response['result']['ip'], response['result']['streamKey'])

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

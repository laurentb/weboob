# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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


from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.backend import Module, BackendConfig

from .browser import NolifeTVBrowser
from .video import NolifeTVVideo

import urllib
import time
from hashlib import md5

__all__ = ['NolifeTVModule']


class NolifeTVModule(Module, CapVideo, CapCollection):
    NAME = 'nolifetv'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = 'NolifeTV French video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = NolifeTVBrowser
    CONFIG = BackendConfig(Value('username',                label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           Value('quality', label='Quality',
                                 choices = { '1':'LQ', '2':'HQ', '3':'TV', '4':'720p', '5':'1080p' },
                                 default = '5' ))

    def create_default_browser(self):
        username = self.config['username'].get()
        if username:
            password = self.config['password'].get()
        else:
            password = None
        return self.create_browser(username, password)

    def iter_resources(self, objs, split_path):
        with self.browser:
            if BaseVideo in objs:
                collection = self.get_collection(objs, split_path)
                if collection.path_level == 0:
                    yield Collection([u'theme'], u'Par theme')
                    yield Collection([u'type'], u'Par type')
                    yield Collection([u'latest'], u'Latest NolifeTV videos')
                if collection.path_level == 1:
                    if split_path[0] == 'latest':
                        for vid in self.browser.get_latest():
                            yield vid
                    else:
                        for cat in self.browser.iter_category(split_path[0]):
                            yield cat
                if collection.path_level == 2:
                    for cat in self.browser.iter_family(split_path[0], split_path[1]):
                        yield cat
                if collection.path_level == 3:
                    for cat in self.browser.iter_video(split_path[2]):
                        yield cat

    def validate_collection(self, objs, collection):
        if BaseVideo in objs:
            if collection.path_level == 0:
                return
            if collection.path_level == 1 and collection.split_path[0] in [u'theme', u'type', u'latest']:
                return
            if collection.path_level > 1:
                return
        raise CollectionNotFound(collection.split_path)

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    def fill_video(self, video, fields):
        with self.browser:
            self.browser.get_video(NolifeTVVideo.id2url(video.id), video)

        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

        if 'url' in fields:
            with self.browser:
                video.url = self.get_url(video.id, self.config['quality'].get())
        return video

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        with self.browser:
            return self.browser.search_videos(pattern)

    OBJECTS = { NolifeTVVideo: fill_video }

    SALT = 'a53be1853770f0ebe0311d6993c7bcbe'

    def genkey(self):
        # This website is really useful to get info: http://www.showmycode.com/
        timestamp = str(int(time.time()))
        skey = md5(md5(timestamp).hexdigest() + self.SALT).hexdigest()
        return skey, timestamp

    def get_url(self, id, quality):
        skey, timestamp = self.genkey()
        self.browser.readurl('http://online.nolife-tv.com/_nlfplayer/api/api_player.php',
                             'quality=%s&a=EML&skey=%s&id%%5Fnlshow=%s&timestamp=%s' % (quality, skey, id, timestamp))

        skey, timestamp = self.genkey()
        data = self.browser.readurl('http://online.nolife-tv.com/_nlfplayer/api/api_player.php',
                                    'quality=%s&a=UEM%%7CSEM%%7CMEM%%7CCH%%7CSWQ&skey=%s&id%%5Fnlshow=%s&timestamp=%s' % (quality, skey, id, timestamp))
        values = dict([urllib.splitvalue(s) for s in data.split('&')])

        if 'url' not in values:
            return None
        return unicode(values['url'])

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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

from base64 import b64encode

from weboob.browser import PagesBrowser, URL
from weboob.browser.exceptions import HTTPNotFound
from weboob.capabilities.base import NotAvailable
from weboob.tools.compat import urljoin, quote_plus

from .pages import VideoJsonPage, CategoriesPage, ListPage, APIPage, XMLAPIPage

import time
import hmac
from hashlib import sha1


__all__ = ['VimeoBrowser']


class VimeoBrowser(PagesBrowser):

    BASEURL = 'https://vimeo.com'
    APIURL = 'http://vimeo.com/api/rest/v2'
    CONSUMER_KEY = 'ae4ac83f9facda375a72fed704a3643a'
    CONSUMER_SECRET = 'b6072a4aba1eaaed'

    video_url = URL(r'https://player.vimeo.com/video/(?P<_id>.*)/config', VideoJsonPage)

    list_page = URL(r'categories/(?P<category>.*)/videos/.*?',
                    ListPage)
    categories_page = URL('categories', CategoriesPage)

    api_page = URL('https://api.vimeo.com/search\?filter_mature=191&filter_type=clip&sort=featured&direction=desc&page=(?P<page>\d*)&per_page=20&sizes=590x332&_video_override=true&c=b&query=&filter_category=(?P<category>\w*)&fields=search_web%2Cmature_hidden_count&container_fields=parameters%2Ceffects%2Csearch_id%2Cstream_id%2Cmature_hidden_count', APIPage)

    _api = URL(APIURL, XMLAPIPage)

    def __init__(self, method, quality, *args, **kwargs):
        self.method = method
        self.quality = quality
        PagesBrowser.__init__(self, *args, **kwargs)

    def fill_video_infos(self, _id, video=None):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'method': 'vimeo.videos.getInfo',
                'video_id': _id}
        self._prepare_request(self.APIURL, method='POST', headers=headers, data=data)
        return self._api.go(data=data).fill_video_infos(obj=video)

    def get_video(self, _id, video=None):
        video = self.fill_video_infos(_id, video)
        if video._is_hd == "0":
            video._quality = 2
        else:
            video._quality = self.quality
        video._method = self.method
        return self.fill_video_url(video)

    def fill_video_url(self, video):
        self._setup_session(self.PROFILE)
        try:
            video = self.video_url.open(_id=video.id).fill_url(obj=video)
            if self.method == u'hls':
                streams = []
                for item in self.read_url(video.url):
                    item = item.decode('ascii')
                    if not item.startswith('#') and item.strip():
                        streams.append(item)

                if streams:
                    streams.reverse()
                    url = streams[self.quality] if self.quality < len(streams) else streams[0]
                    video.url = urljoin(video.url, url)
                else:
                    video.url = NotAvailable
            return video
        except HTTPNotFound:
            return video

    def read_url(self, url):
        r = self.open(url, stream=True)
        buf = r.iter_lines()
        return buf

    def search_videos(self, pattern, sortby):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'method': 'vimeo.videos.search',
                'sort': 'relevant',
                'page': '1',
                'full_response': '1',
                'query': quote_plus(pattern.encode('utf-8'))}

        self._prepare_request(self.APIURL, method='POST', headers=headers, data=data)
        return self._api.go(data=data).iter_videos()

    def get_channels(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'method': 'vimeo.channels.getAll',
                'page': '1',
                'sort': 'most_subscribed'}
        # 'newest', 'oldest', 'alphabetical', 'most_videos', 'most_subscribed', 'most_recently_updated'
        self._prepare_request(self.APIURL, method='POST', headers=headers, data=data)
        return self._api.go(data=data).iter_channels()

    def get_channel_videos(self, channel):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'method': 'vimeo.channels.getVideos',
                'sort': 'newest',  # 'oldest', 'most_played', 'most_commented', 'most_liked'
                'page': '1',
                'channel_id': channel,
                'full_response': '1'}
        self._prepare_request(self.APIURL, method='POST', headers=headers, data=data)
        return self._api.go(data=data).iter_videos()

    def get_categories(self):
        self._setup_session(self.PROFILE)
        return self.categories_page.go().iter_categories()

    def get_category_videos(self, category):
        token = self.list_page.go(category=category).get_token()
        self.session.headers.update({"Authorization": "jwt %s" % token,
                                     "Accept": "application/vnd.vimeo.*+json;version=3.3"})
        return self.api_page.go(page=1, category=category).iter_videos()

    def _create_authorization(self, url, method, params=None):
        def _percent_encode(s):
            result = quote_plus(s).replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
            # the implementation of the app has a bug. someone double escaped the '@' so we have to correct this
            # on our end.
            result = result.replace('%40', '%2540')
            return result

        def _compute_signature(s):
            key = _percent_encode(self.CONSUMER_SECRET) + '&' + _percent_encode('')
            key = key.encode('ascii')
            s = s.encode('ascii')
            a = hmac.new(key, s, sha1)
            sig = b64encode(a.digest()).decode('ascii')
            sig = sig.rstrip('\n')
            return sig

        def _normalize_parameters(_params):
            sorted_keys = sorted(_params.keys())
            list_of_params = []
            for key in sorted_keys:
                value = _params[key]
                # who wrote the android app should burn in hell! No clue of correct encoding - make up your mind
                if url == 'https://secure.vimeo.com/oauth/access_token' and key != 'x_auth_password':
                    list_of_params.append('%s=%s' % (key, value))
                    pass
                else:
                    list_of_params.append('%s=%s' % (key, _percent_encode(value)))
                    pass
                pass
            return '&'.join(list_of_params)

        if not params:
            params = {}
            pass

        all_params = {'oauth_consumer_key': self.CONSUMER_KEY,
                      'oauth_signature_method': 'HMAC-SHA1',
                      'oauth_timestamp': str(time.time()),
                      'oauth_nonce': str(time.time()),
                      'oauth_version': '1.0'}
        all_params.update(params)

        base_string = _percent_encode(method.upper())
        base_string += '&'
        base_string += _percent_encode(url)
        base_string += '&'
        base_string += _percent_encode(_normalize_parameters(all_params))

        all_params['oauth_signature'] = _compute_signature(base_string)

        authorization = []
        for key in all_params:
            if key.startswith('oauth_'):
                authorization.append('%s="%s"' % (key, _percent_encode(all_params[key])))
                pass
            pass
        return {'Authorization': 'OAuth %s' % (', '.join(authorization))}

    def _prepare_request(self, url, method='GET', headers={}, data={}):
        _headers = {
            'User-Agent': 'VimeoAndroid/1.1.42 (Android ver=4.4.2 sdk=19; Model\
            samsung GT-I9505; Linux 3.4.0-3423977 armv7l)',
            'Host': 'vimeo.com',
            'Accept-Encoding': 'gzip, deflate'}
        self.session.headers.update(_headers)
        self.session.headers.update(headers)
        self.session.headers.update(self._create_authorization(url, method, data))

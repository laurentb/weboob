# -*- coding: utf-8 -*-

# Copyright(C) 2014      Roger Philibert
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import re

from weboob.browser.browsers import DomainBrowser, APIBrowser
from weboob.browser.filters.standard import CleanText
from weboob.browser.pages import HTMLPage
from weboob.browser.profiles import IPhone, Android
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.tools.json import json


__all__ = ['TinderBrowser', 'FacebookBrowser']


class FacebookBrowser(DomainBrowser):
    BASEURL = 'https://graph.facebook.com'
    PROFILE = Android()

    CLIENT_ID = "464891386855067"
    access_token = None
    info = None

    def login(self, username, password):
        self.location('https://www.facebook.com/v2.6/dialog/oauth?redirect_uri=fb464891386855067%3A%2F%2Fauthorize%2F&display=touch&state=%7B%22challenge%22%3A%22IUUkEUqIGud332lfu%252BMJhxL4Wlc%253D%22%2C%220_auth_logger_id%22%3A%2230F06532-A1B9-4B10-BB28-B29956C71AB1%22%2C%22com.facebook.sdk_client_state%22%3Atrue%2C%223_method%22%3A%22sfvc_auth%22%7D&scope=user_birthday%2Cuser_photos%2Cuser_education_history%2Cemail%2Cuser_relationship_details%2Cuser_friends%2Cuser_work_history%2Cuser_likes&response_type=token%2Csigned_request&default_audience=friends&return_scopes=true&auth_type=rerequest&client_id=' + self.CLIENT_ID + '&ret=login&sdk=ios&logger_id=30F06532-A1B9-4B10-BB28-B29956C71AB1&ext=1470840777&hash=AeZqkIcf-NEW6vBd')
        page = HTMLPage(self, self.response)
        form = page.get_form()
        form['email'] = username
        form['pass'] = password
        form.submit(allow_redirects=False)
        if 'Location' not in self.response.headers:
            raise BrowserIncorrectPassword()

        self.location(self.response.headers['Location'])

        page = HTMLPage(self, self.response)
        if len(page.doc.xpath('//td/div[has-class("s")]')) > 0:
            raise BrowserIncorrectPassword(CleanText('//td/div[has-class("s")]')(page.doc))

        form = page.get_form(nr=0, submit='//input[@name="__CONFIRM__"]')
        form.submit(allow_redirects=False)

        m = re.search('access_token=([^&]+)&', self.response.headers['Location'])
        if m:
            self.access_token = m.group(1)
        else:
            raise ParseError('Unable to find access_token')

        self.info = self.request('/me')

    def request(self, url, *args, **kwargs):
        url += '?access_token=' + self.access_token
        self.location(self.absurl(url, base=True), *args, **kwargs)
        return json.loads(self.response.content)


class TinderBrowser(APIBrowser):
    BASEURL = 'https://api.gotinder.com/'
    PROFILE = IPhone('Tinder/3.0.2')

    recs = []

    def __init__(self, facebook, location, *args, **kwargs):
        super(TinderBrowser, self).__init__(*args, **kwargs)
        self.facebook = facebook

        data = self.request('/v2/auth/login/facebook', data={'token': facebook.access_token})['data']
        self.session.headers['Authorization'] = 'Token token="%s"' % data['api_token']
        self.session.headers['X-Auth-Token'] = data['api_token']

        me = self.request('/v2/profile',
                          params={'include': 'account,boost,email_settings,instagram,likes,notifications,plus_control,products,purchase,spotify,super_likes,tinder_u,travel,tutorials,user'})
        self.my_id = me['data']['user']['_id']
        self.my_name = me['data']['user']['name']

        if location:
            lat, lon = location.split(',')
            self.request('/user/ping', data={'lat': lat, 'lon': lon})

    def get_threads(self):
        resp = self.request('/updates', data={'last_activity_date': '2014-05-01T06:13:16.971Z'})
        matches = [m for m in resp['matches'] if 'last_activity_date' in m]
        return sorted(matches, key=lambda m: m['last_activity_date'], reverse=True)

    def post_message(self, match_id, content):
        self.request('/user/matches/%s' % match_id, data={'message': content})

    def update_recs(self):
        resp = self.request('/user/recs')

        try:
            self.recs = resp['results']
        except KeyError:
            self.recs = []

    def like_profile(self):
        if len(self.recs) == 0:
            self.update_recs()
        if len(self.recs) == 0:
            return 60

        profile = self.recs.pop()

        if 'tinder_rate_limited' in profile['_id']:
            self.logger.info(profile['bio'])
            return 600

        resp = self.request('/like/%s' % profile['_id'])

        if resp['match']:
            self.logger.error('Match with %s!' % profile['name'])
        else:
            self.logger.info('Liked %s (%r)' % (profile['name'], profile.get('common_likes', '')))

        if len(self.recs) > 0:
            return 1
        else:
            return 60

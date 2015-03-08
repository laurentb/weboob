# -*- coding: utf-8 -*-

# Copyright(C) 2014      Roger Philibert
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


import re

from weboob.browser.browsers import DomainBrowser, APIBrowser
from weboob.browser.pages import HTMLPage
from weboob.browser.profiles import IPhone
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.json import json


__all__ = ['TinderBrowser', 'FacebookBrowser']


class FacebookBrowser(DomainBrowser):
    BASEURL = 'https://graph.facebook.com'

    CLIENT_ID = "464891386855067"
    access_token = None
    info = None

    def login(self, username, password):
        self.location('https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=https://www.facebook.com/connect/login_success.html&scope=basic_info,email,public_profile,user_about_me,user_activities,user_birthday,user_education_history,user_friends,user_interests,user_likes,user_location,user_photos,user_relationship_details&response_type=token' % self.CLIENT_ID)
        page = HTMLPage(self, self.response)
        form = page.get_form('//form[@id="login_form"]')
        form['email'] = username
        form['pass'] = password
        form['persistent'] = 1
        form.submit(allow_redirects=False)
        if 'Location' not in self.response.headers:
            raise BrowserIncorrectPassword()

        self.location(self.response.headers['Location'])
        m = re.search('access_token=([^&]+)&', self.url)
        if m:
            self.access_token = m.group(1)

        self.info = self.request('/me')

    def request(self, url, *args, **kwargs):
        url += '?access_token=' + self.access_token
        self.location(self.absurl(url, base=True), *args, **kwargs)
        return json.loads(self.response.content)


class TinderBrowser(APIBrowser):
    BASEURL = 'https://api.gotinder.com/'
    PROFILE = IPhone('Tinder/3.0.2')

    recs = []

    def __init__(self, facebook, *args, **kwargs):
        super(TinderBrowser, self).__init__(*args, **kwargs)
        self.facebook = facebook

        me = self.request('/auth', data={'facebook_id': facebook.info['id'], 'facebook_token': facebook.access_token})
        self.session.headers['Authorization'] = 'Token token="%s"' % me['token']
        self.session.headers['X-Auth-Token'] = me['token']

        self.my_id = me['user']['_id']
        self.my_name = me['user']['name']

    def get_threads(self):
        resp = self.request('/updates', data={'last_activity_date': '2014-05-01T06:13:16.971Z'})
        return sorted(resp['matches'], key=lambda m: m['last_activity_date'], reverse=True)

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
            return

        profile = self.recs.pop()

        if 'tinder_rate_limited' in profile['_id']:
            self.logger.info(profile['bio'])
            return 600

        resp = self.request('/like/%s' % profile['_id'])

        if resp['match']:
            self.logger.error('Match with %s!' % profile['name'])
        else:
            self.logger.info('Liked %s (%r)' % (profile['name'], profile['common_likes']))

        if len(self.recs) > 0:
            return 1
        else:
            return 60

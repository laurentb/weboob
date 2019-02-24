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

from weboob.browser import DomainBrowser
from weboob.browser.exceptions import ClientError
from weboob.browser.pages import HTMLPage
from weboob.browser.profiles import Profile
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.json import json


__all__ = ['PlayMeBrowser', 'FacebookBrowser']


class NoCredits(Exception): pass


class FacebookBrowser(DomainBrowser):
    BASEURL = 'https://graph.facebook.com'

    CLIENT_ID = "149987128492319"
    access_token = None
    info = None

    def login(self, username, password):
        self.location('https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=https://www.facebook.com/connect/login_success.html&scope=email,user_birthday,user_friends,public_profile,user_photos,user_likes&response_type=token' % self.CLIENT_ID)
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
        r = self.location(self.absurl(url, base=True), *args, **kwargs)
        return json.loads(r.content)


class IPhoneClient(Profile):
    def setup_session(self, session):
        session.headers["Accept-Language"] = "en;q=1, fr;q=0.9, de;q=0.8, ja;q=0.7, nl;q=0.6, it;q=0.5"
        session.headers["Accept"] = "*/*"
        session.headers["User-Agent"] = "PlayMe/3.0.2 (iPhone; iOS 7.1; Scale/2.00)"
        session.headers["Accept-Encoding"] = "gzip, deflate"
        session.headers["Content-Type"] = "application/json"


class PlayMeBrowser(DomainBrowser):
    BASEURL = 'https://api2.goplayme.com/'
    PROFILE = IPhoneClient()
    VERIFY = False

    recs = []

    def __init__(self, facebook, *args, **kwargs):
        super(PlayMeBrowser, self).__init__(*args, **kwargs)
        self.facebook = facebook

        profile_picture = 'http%3A%2F%2Fgraph.facebook.com%2F' + facebook.info['id'] + '%2Fpicture%3Fwidth%3D600%26height%3D600'
        me = self.request('/auth/facebook/callback?access_token=%s&profile_picture=%s' % (facebook.access_token, profile_picture))
        self.session.headers['Authorization'] = 'Token token="%s"' % me['token']

        self.my_id = me['id']
        self.my_name = me['name']
        self.credits = me['credits']['count']

    def get_threads(self):
        r = self.request('/users/%s/contacts' % self.my_id)
        if 'status' in r:
            return []
        return reversed(r)

    def get_thread_messages(self, contact_id):
        return self.request('/messages/%s' % contact_id)

    def get_user(self, contact_id):
        return self.request('/users/%s' % contact_id)

    def post_message(self, contact_id, content):
        self.request('/messages', data={'id': contact_id, 'msg': content})

    def request(self, *args, **kwargs):
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])

        r = self.location(*args, **kwargs)
        return json.loads(r.content)

    def find_users(self, lat, lon):
        r = self.request('/users/?lat=%s&lon=%s&type=full' % (lat, lon))
        return r['pending'] + r['history']

    def get_theme(self):
        r = self.request('/questions')
        for t in r:
            if t['theme']['is_vip']:
                continue
            return t

    def challenge(self, user_id):
        try:
            r = self.request('/users/%s/challenge/%s' % (self.my_id, user_id))
        except ClientError as e:
            r = json.loads(e.response.content)
            self.credits = r['credits']['count']
            raise NoCredits(r['credits']['next_restore_in_seconds'])

        if isinstance(r, list) and 'questions' in r[0]:
            t = r[0]
        else:
            t = self.get_theme()
            self.credits = r['credits']['count']

        data = {}
        data['theme'] = {'id': t['theme']['id'], 'is_vip': 0}
        data['questions'] = [q['id'] for q in t['questions']][:5]
        data['answers'] = [{'duration': 1000, 'result': 1} for q in t['questions'][:5]]

        self.request('/users/%s/challenge/%s' % (self.my_id, user_id), data=data)

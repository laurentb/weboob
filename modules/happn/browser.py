# -*- coding: utf-8 -*-

# Copyright(C) 2015      Roger Philibert
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

from weboob.browser.browsers import DomainBrowser
from weboob.browser.profiles import IPhone
from weboob.browser.pages import HTMLPage
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.json import json


__all__ = ['HappnBrowser', 'FacebookBrowser']


class FacebookBrowser(DomainBrowser):
    BASEURL = 'https://graph.facebook.com'

    CLIENT_ID = "247294518656661"
    access_token = None
    info = None

    def login(self, username, password):
        self.location('https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=fbconnect://success&scope=email,user_birthday,user_friends,public_profile,user_photos,user_likes&response_type=token' % self.CLIENT_ID)
        page = HTMLPage(self, self.response)
        form = page.get_form('//form[@id="login_form"]')
        form['email'] = username
        form['pass'] = password
        form['persistent'] = 1
        form.submit(allow_redirects=False)
        if 'Location' not in self.response.headers:
            raise BrowserIncorrectPassword()

        self.location(self.response.headers['Location'])

        params = {}
        for inp in re.findall(r'input [^>]*type=\\"hidden\\" [^>]*>', self.response.text, re.MULTILINE):
            m = re.search(r'name=\\"([^"]+)\\"', inp)
            m2 = re.search(r'value=\\"([^"]+)\\"', inp)
            params[m.group(1)] = m2.group(1).replace('\\', '') if m2 else ''
        params['__CONFIRM__'] = 1
        m = re.search(r'rel=\\"async\\" ajaxify=\\"([^"]+)\\"', self.response.text, re.MULTILINE)
        if m:
            uri = m.group(1).replace('\\', '')
        self.location(uri, data=params)
        m = re.search('access_token=([^&]+)&', self.response.text)
        if m:
            self.access_token = m.group(1)

        self.info = self.request('/me')

    def request(self, url, *args, **kwargs):
        url += '?access_token=' + self.access_token
        r = self.location(self.absurl(url, base=True), *args, **kwargs)
        return json.loads(r.content)


class HappnBrowser(DomainBrowser):
    BASEURL = 'https://api.happn.fr/'
    PROFILE = IPhone('Happn/3.0.2')

    recs = []

    def __init__(self, facebook, *args, **kwargs):
        super(HappnBrowser, self).__init__(*args, **kwargs)
        self.facebook = facebook

        r = self.request('/connect/oauth/token', data={
            'client_id': 'FUE-idSEP-f7AqCyuMcPr2K-1iCIU_YlvK-M-im3c',
            'client_secret': 'brGoHSwZsPjJ-lBk0HqEXVtb3UFu-y5l_JcOjD-Ekv',
            'grant_type': 'assertion',
            'assertion_type': 'facebook_access_token',
            'assertion': facebook.access_token,
            'scope': 'mobile_app',
        })
        self.session.headers['Authorization'] = 'OAuth="%s"' % r['access_token']

        self.my_id = r['user_id']
        self.refresh_token = r['refresh_token']

        me = self.request('/api/users/me')
        self.my_name = me['data']['name']

    def request(self, *args, **kwargs):
        r = self.location(*args, **kwargs)
        return r.json()

    def get_contact(self, contact_id):
        return self.request('/api/users/%s?fields=birth_date,first_name,last_name,display_name,login,credits,referal,matching_preferences,notification_settings,unread_conversations,about,is_accepted,age,job,workplace,school,modification_date,profiles.mode(0).width(1000).height(1000).fields(url,width,height,mode),last_meet_position,my_relation,is_charmed,distance,gender' % contact_id)['data']

    def get_threads(self):
        return self.request('/api/users/me/conversations')['data']

    def get_thread(self, id):
        r = self.request('/api/users/me/conversations/%s?fields=id,messages.fields(id,message,creation_date,sender.fields(id)),participants.fields(user.fields(birth_date,first_name,last_name,display_name,login,credits,referal,matching_preferences,notification_settings,unread_conversations,about,is_accepted,age,job,workplace,school,modification_date,profiles.mode(0).width(1000).height(1000).fields(url,width,height,mode),last_meet_position,my_relation,is_charmed,distance,gender))' % id)['data']
        return r

    def post_message(self, thread_id, content):
        self.request('/api/conversations/%s/messages/' % thread_id, data={'message': content})

    def find_users(self):
        return self.request('/api/users/me/notifications?fields=id,is_pushed,lon,actions,creation_date,is_notified,lat,modification_date,notification_type,nb_times,notifier.fields(id,job,is_accepted,workplace,my_relation,distance,gender,my_conversation,is_charmed,nb_photos,last_name,first_name,age),notified.fields(is_accepted,is_charmed)')['data']

    def accept(self, id):
        self.request('/api/users/me/accepted/%s' % id, method='POST')

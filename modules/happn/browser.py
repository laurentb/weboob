# -*- coding: utf-8 -*-

# Copyright(C) 2015      Roger Philibert
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

from weboob.browser.browsers import DomainBrowser
from weboob.browser.profiles import IPhone
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.tools.json import json


__all__ = ['HappnBrowser', 'FacebookBrowser']


class FacebookBrowser(DomainBrowser):
    BASEURL = 'https://graph.facebook.com'

    CLIENT_ID = "247294518656661"
    PROFILE = IPhone('Happn/3.0.2')
    access_token = None
    info = None

    def login(self, username, password):
        self.location('https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=fbconnect://success&scope=email,user_birthday,user_friends,public_profile,user_photos,user_likes&response_type=token' % self.CLIENT_ID)
        page = HTMLPage(self, self.response)
        form = page.get_form('//form[@id="login_form"]')
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
        url += '&' if ('?' in url) else '?'
        url += 'access_token=' + self.access_token
        r = self.location(self.absurl(url, base=True), *args, **kwargs)
        return json.loads(r.content)


class HappnBrowser(DomainBrowser):
    BASEURL = 'https://api.happn.fr/'
    PROFILE = IPhone('Happn/18.3.1')
    ALLOW_REFERRER = False

    recs = []

    def __init__(self, facebook, *args, **kwargs):
        super(HappnBrowser, self).__init__(*args, **kwargs)
        self.facebook = facebook
        self.session.headers['User-Agent'] = 'Happn/18.3.1 AndroidSDK/11'

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

        self.request('/api/auth/proof', data={'facebook_access_token': facebook.access_token})

        r = self.request('/api/users/%s/devices/' % self.my_id,
                     data={"adid": "78462200ada313bb943b01800819a1d5",
                           "android_id": "fe26ca3be49bbbf6",
                           "app_build": "20.14.0",
                           "country_id": "FR",
                           "idfa": "2265540e-7a5f-4308-9c69-3afd2f608a2e",
                           "language_id": "fr",
                           "os_build": 23,
                           "token": "",
                           "type": "android"
                          })
        self.device_id = r['data']['id']

        me = self.request('/api/users/me')
        self.my_name = me['data']['nickname']

    def request(self, *args, **kwargs):
        r = self.location(*args, **kwargs)
        return r.json()

    def get_facebook(self, facebook_id):
        data = self.facebook.request('https://graph.facebook.com/%s' % facebook_id)
        if not 'link' in data:
            data['link'] = ('https://www.facebook.com/%s' % data['username']) if 'username' in data else ''
        likes = self.facebook.request('https://graph.facebook.com/%s/likes?limit=10000' % facebook_id)
        data['likes'] = [like['name'] for like in likes['data']]
        data['infos'] = self.facebook.request('https://graph.facebook.com/v2.3/%s?fields=about,address,age_range,bio,birthday,devices,education,email,favorite_athletes,favorite_teams,hometown,inspirational_people,install_type,interested_in,is_verified,languages,location,meeting_for,political,relationship_status,religion,significant_other,sports,quotes,timezone,updated_time,verified,website,work' % facebook_id)

        return data

    def get_contact(self, contact_id):
        data = self.request('/api/users/%s?fields=birth_date,first_name,last_name,nickname,login,credits,referal,matching_preferences,notification_settings,unread_conversations,about,is_accepted,age,job,workplace,school,modification_date,profiles.mode(0).width(1000).height(1000).fields(url,width,height,mode),last_meet_position,my_relation,is_charmed,distance,gender' % contact_id)['data']
        return data

    def get_threads(self):
        return self.request('/api/users/me/conversations')['data']

    def get_thread(self, id):
        r = self.request('/api/users/%s/conversations/%s?fields=id,messages.limit(100).fields(id,message,creation_date,sender.fields(id)),participants.fields(user.fields(birth_date,first_name,last_name,nickname,credits,referal,matching_preferences,notification_settings,unread_conversations,about,is_accepted,age,job,workplace,school,modification_date,profiles.mode(0).width(1000).height(1000).fields(url,width,height,mode),last_meet_position,my_relation,is_charmed,distance,gender))' % (self.my_id, id))['data']
        return r

    def post_message(self, thread_id, content):
        self.request('/api/conversations/%s/messages/' % thread_id, data={'message': content})

    def find_users(self):
        return self.request('/api/users/me/notifications?types=468&fields=id,is_pushed,lon,actions,creation_date,is_notified,lat,modification_date,notification_type,nb_times,notifier.fields(id,job,is_accepted,workplace,my_relation,distance,gender,my_conversation,is_charmed,nb_photos,last_name,first_name,age),notified.fields(is_accepted,is_charmed)')['data']

    def accept(self, id):
        self.request('/api/users/me/accepted/%s' % id, method='POST')

    def set_position(self, lat, lng):
        r = self.request('/api/users/%s/devices/%s' % (self.my_id, self.device_id), method='PUT',
                         data={'latitude': lat, 'longitude': lng, 'altitude': 0.0})

        return r['data']['position']

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2016 Roger Philibert
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

from weboob.browser import LoginBrowser, URL
from weboob.browser.browsers import DomainBrowser
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.tools.json import json

__all__ = ['OkCBrowser']


def need_login(func):
    def inner(browser, *args, **kwargs):
        if not browser.access_token:
            browser.do_login()
        return func(browser, *args, **kwargs)
    return inner


class FacebookBrowser(DomainBrowser):
    BASEURL = 'https://graph.facebook.com'

    access_token = None

    def login(self, username, password):
        self.location('https://www.facebook.com/v2.9/dialog/oauth?app_id=484681304938818&auth_type=rerequest&channel_url=https%3A%2F%2Fstaticxx.facebook.com%2Fconnect%2Fxd_arbiter.php%3Fversion%3D44%23cb%3Df33dd8340f36618%26domain%3Dwww.okcupid.com%26origin%3Dhttps%253A%252F%252Fwww.okcupid.com%252Ff5818a5f355be8%26relation%3Dopener&client_id=484681304938818&display=popup&domain=www.okcupid.com&e2e=%7B%7D&fallback_redirect_uri=https%3A%2F%2Fwww.okcupid.com%2Flogin&locale=en_US&origin=1&redirect_uri=https%3A%2F%2Fstaticxx.facebook.com%2Fconnect%2Fxd_arbiter.php%3Fversion%3D44%23cb%3Df2ce4ca90b82cb4%26domain%3Dwww.okcupid.com%26origin%3Dhttps%253A%252F%252Fwww.okcupid.com%252Ff5818a5f355be8%26relation%3Dopener%26frame%3Df3f40f304ac5e9&response_type=token%2Csigned_request&scope=email%2Cuser_birthday%2Cuser_photos&sdk=joey&version=v2.9')

        page = HTMLPage(self, self.response)
        form = page.get_form('//form[@id="login_form"]')
        form['email'] = username
        form['pass'] = password
        self.session.headers['cookie-installing-permission'] = 'required'
        self.session.cookies['wd'] = '640x1033'
        self.session.cookies['act'] = '1563018648141%2F0'
        form.submit(allow_redirects=False)
        if 'Location' not in self.response.headers:
            raise BrowserIncorrectPassword()

        self.location(self.response.headers['Location'])

        page = HTMLPage(self, self.response)
        if len(page.doc.xpath('//td/div[has-class("s")]')) > 0:
            raise BrowserIncorrectPassword(CleanText('//td/div[has-class("s")]')(page.doc))

        script = page.doc.xpath('//script')[0].text

        m = re.search('access_token=([^&]+)&', script)
        if m:
            self.access_token = m.group(1)
        else:
            raise ParseError('Unable to find access_token')


class OkCBrowser(LoginBrowser):
    BASEURL = 'https://www.okcupid.com'

    login = URL('/login')
    threads = URL('/1/apitun/connections/messages/incoming')
    messages = URL('/1/apitun/messages/conversations/(?P<thread_id>\d+)')
    thread_delete = URL(r'/1/apitun/messages/conversations/(?P<thread_id>\d+)/delete')
    message_send = URL('/1/apitun/messages/send')
    quickmatch = URL(r'/quickmatch\?okc_api=1')
    like = URL(r'/1/apitun/profile/(?P<user_id>\d+)/like')
    profile = URL(r'/1/apitun/profile/(?P<user_id>\d+)')

    access_token = None
    me = None

    def __init__(self, username, password, facebook, *args, **kwargs):
        self.facebook = facebook

        super(OkCBrowser, self).__init__(username, password, *args, **kwargs)

    def do_login(self):
        if self.facebook:
            r = self.login.go(data={'facebook_access_token': self.facebook.access_token, 'okc_api': 1}).json()

        else:
            r = self.login.go(data={'username': self.username, 'password': self.password, 'okc_api': 1}).json()

        if not 'oauth_accesstoken' in r:
            raise BrowserIncorrectPassword(r['status_str'])

        self.access_token = r['oauth_accesstoken']
        self.me = {'userid':    r['userid'],
                   'username':  r['screenname'],
                  }
        self.session.headers['X-OkCupid-Platform'] = 'DESKTOP'
        self.session.headers['X-Requested-With'] = 'XMLHttpRequest'
        self.session.headers['Authorization'] = 'Bearer %s' % self.access_token

    @need_login
    def get_threads_list(self):
        return self.threads.go().json()['data']

    @need_login
    def get_thread_messages(self, thread_id):
        r = self.messages.go(thread_id=thread_id, params={'limit': 20}, headers={'endpoint_version': '2'}).json()
        return r

    @need_login
    def post_message(self, thread_id, content):
        data = {'body': content,
                'profile_tab': '',
                'receiverid': thread_id,
                'service': 'mailbox',
                'source': 'desktop_global'}

        self.message_send.go(params={'access_token': self.access_token},
                             data=json.dumps(data))

    @need_login
    def delete_thread(self, thread_id):
        self.thread_delete.go(method='POST', thread_id=thread_id)

    @need_login
    def find_match_profile(self):
        r = self.quickmatch.go().json()
        return r['tracking_userid']

    @need_login
    def do_rate(self, user_id):
        self.like.go(method='POST', user_id=user_id)

    @need_login
    def get_profile(self, username):
        return self.profile.go(user_id=username).json()

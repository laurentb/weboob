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

from weboob.browser import LoginBrowser, URL
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.json import json


__all__ = ['OkCBrowser']


def need_login(func):
    def inner(browser, *args, **kwargs):
        if not browser.access_token:
            browser.do_login()
        return func(browser, *args, **kwargs)
    return inner


class OkCBrowser(LoginBrowser):
    BASEURL = 'https://www.okcupid.com'

    login = URL('/login')
    threads = URL('/messages')
    messages = URL('/apitun/messages/conversations/global_messaging')
    thread_delete = URL(r'/1/apitun/messages/conversations/(?P<thread_id>\d+)/delete')
    message_send = URL('/apitun/messages/send')
    quickmatch = URL(r'/quickmatch\?okc_api=1')
    like = URL(r'/1/apitun/profile/(?P<user_id>\d+)/like')
    profile = URL(r'/apitun/profile/(?P<user_id>\d+)')
    full_profile = URL(r'/profile/(?P<username>.*)\?okc_api=1')

    access_token = None
    me = None

    def do_login(self):
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
    def get_threads_list(self, folder=1):
        return self.threads.go(params={'okc_api': 1, 'folder': folder, 'messages_dropdown_ajax': 1}).json()

    @need_login
    def get_thread_messages(self, thread_id):
        r = self.messages.go(params={'access_token': self.access_token,
                                     '_json': '{"userids":["%s"]}' % thread_id}).json()
        return r[thread_id]

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
    def get_username(self, user_id):
        return self.profile.go(user_id=user_id).json()['username']

    @need_login
    def get_profile(self, username):
        if username.isdigit():
            username = self.get_username(username)

        return self.full_profile.go(username=username).json()

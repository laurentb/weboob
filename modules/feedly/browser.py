# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from weboob.tools.json import json
from weboob.capabilities.base import UserError
from weboob.capabilities.collection import Collection
from weboob.browser import LoginBrowser, URL, need_login
from .pages import EssentialsPage, TokenPage, ContentsPage, PreferencesPage, MarkerPage


__all__ = ['FeedlyBrowser']


class FeedlyBrowser(LoginBrowser):
    BASEURL = 'https://www.feedly.com/'

    essentials = URL('https://s3.feedly.com/essentials/essentials_fr.json', EssentialsPage)
    token = URL('v3/auth/token', TokenPage)
    contents = URL('v3/streams/contents', ContentsPage)
    preferences = URL('v3/preferences', PreferencesPage)
    marker = URL('v3/markers', MarkerPage)

    def __init__(self, username, password, login_browser, *args, **kwargs):
        super(FeedlyBrowser, self).__init__(username, password, *args, **kwargs)
        self.user_id = None
        self.login_browser = login_browser

    def do_login(self):
        if self.login_browser:
            if self.login_browser.code is None or self.user_id is None:
                self.login_browser.do_login()
                params = {'code': self.login_browser.code,
                          'client_id': 'feedly',
                          'client_secret': '0XP4XQ07VVMDWBKUHTJM4WUQ',
                          'redirect_uri': 'http://dev.feedly.com/feedly.html',
                          'grant_type': 'authorization_code'}

                token, self.user_id = self.token.go(data=params).get_token()
                self.session.headers['X-Feedly-Access-Token'] = token
        else:
            raise UserError(r'You need to fill your username and password to access this page')

    @need_login
    def iter_threads(self):
        params = {'streamId': 'user/%s/category/global.all' % self.user_id,
                  'unreadOnly': 'true',
                  'ranked': 'newest',
                  'count': '100'}
        return self.contents.go(params=params).get_articles()

    def get_unread_feed(self, url):
        params = {'streamId': url,
                  'backfill': 'true',
                  'boostMustRead': 'true',
                  'unreadOnly': 'true'}
        return self.contents.go(params=params).get_articles()

    def get_categories(self):
        if self.username is not None and self.password is not None:
            return self.get_logged_categories()
        return self.essentials.go().get_categories()

    @need_login
    def get_logged_categories(self):
        user_categories = list(self.preferences.go().get_categories())
        user_categories.append(Collection([u'global.saved'], u'Saved'))
        return user_categories

    def get_feeds(self, category):
        if self.username is not None and self.password is not None:
            return self.get_logged_feeds(category)
        return self.essentials.go().get_feeds(category)

    @need_login
    def get_logged_feeds(self, category):
        if category == 'global.saved':
            type = 'tag'
        else:
            type = 'category'
        url = 'user/%s/%s/%s' % (self.user_id, type, category)
        return self.get_unread_feed(url)

    def get_feed_url(self, category, feed):
        return self.essentials.go().get_feed_url(category, feed)

    @need_login
    def set_message_read(self, _id):
        datas = {'action': 'markAsRead',
                 'type': 'entries',
                 'entryIds': [_id]}
        self.marker.open(data=json.dumps(datas))

# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012 Laurent Bachelier
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


from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound, BrowserIncorrectPassword
from weboob.tools.browser.decorators import id2url, check_url
from weboob.tools.ordereddict import OrderedDict

from weboob.capabilities.paste import PasteNotFound

from .pages import PastePage, PostPage, UserPage, LoginPage
from .paste import PastebinPaste

import urllib
import re

__all__ = ['PastebinBrowser']


class BadAPIRequest(Exception):
    pass


class PastebinBrowser(BaseBrowser):
    DOMAIN = 'pastebin.com'
    ENCODING = 'UTF-8'
    PASTE_URL = 'http://%s/(?P<id>\w+)' % DOMAIN
    API_URL = 'http://%s/api/api_post.php' % DOMAIN
    PAGES = OrderedDict((
            ('http://%s/login' % DOMAIN, LoginPage),
            ('http://%s/u/(?P<username>.+)' % DOMAIN, UserPage),
            ('http://%s/' % DOMAIN, PostPage),
            (PASTE_URL, PastePage),
    ))

    def __init__(self, api_key, *args, **kwargs):
        self.api_key = api_key
        self.user_key = None

        BaseBrowser.__init__(self, *args, **kwargs)

    def fill_paste(self, paste):
        """
        Get as much as information possible from the paste page
        """
        try:
            self.location(paste.page_url, no_login=True)
            return self.page.fill_paste(paste)
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    @id2url(PastebinPaste.id2url)
    @check_url(PASTE_URL)
    def get_paste(self, url):
        _id = re.match('^%s$' % self.PASTE_URL, url).groupdict()['id']
        return PastebinPaste(_id)

    def get_contents(self, _id):
        """
        Get the contents from the raw URL
        This is the fastest and safest method if you only want the content.
        Returns unicode.
        """
        try:
            return self.readurl('http://%s/raw.php?i=%s' % (self.DOMAIN, _id), if_fail='raise').decode(self.ENCODING)
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    def post_paste(self, paste, expiration=None):
        self.home()
        if not self.is_on_page(PostPage):
            self.home()
        self.page.post(paste, expiration=expiration)
        paste.id = self.page.get_id()

    def api_post_paste(self, paste, expiration=None):
        data = {'api_dev_key': self.api_key,
                'api_option': 'paste',
                'api_paste_code': paste.contents.encode(self.ENCODING),
        }
        if self.password:
            data['api_user_key'] = self.api_login()
        if paste.public is True:
            data['api_paste_private'] = '0'
        elif paste.public is False:
            data['api_paste_private'] = '1'
        if paste.title:
            data['api_paste_name'] = paste.title.encode(self.ENCODING)
        if expiration:
            data['api_paste_expire_date'] = expiration
        res = self.readurl(self.API_URL, urllib.urlencode(data)).decode(self.ENCODING)
        self._validate_api_response(res)
        paste.id = re.match('^%s$' % self.PASTE_URL, res).groupdict()['id']

    def api_login(self):
        # "The api_user_key does not expire."
        # TODO store it on disk
        if self.user_key:
            return self.user_key

        data = {'api_dev_key': self.api_key,
                'api_user_name': self.username,
                'api_user_password': self.password
        }
        res = self.readurl('http://%s/api/api_login.php' % self.DOMAIN,
                urllib.urlencode(data)).decode(self.ENCODING)
        try:
            self._validate_api_response(res)
        except BadAPIRequest, e:
            if str(e) == 'invalid login':
                raise BrowserIncorrectPassword()
            else:
                raise e
        self.user_key = res
        return res

    def _validate_api_response(self, res):
        matches = re.match('Bad API request, (?P<error>.+)', res)
        if matches:
            raise BadAPIRequest(matches.groupdict().get('error'))

    def is_logged(self):
        return self.page and self.page.is_logged()

    def login(self):
        self.location('http://%s/login' % self.DOMAIN, no_login=True)
        self.page.login(self.username, self.password)
        if not self.is_logged():
            raise BrowserIncorrectPassword()

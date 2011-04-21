# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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


from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound
from weboob.tools.browser.decorators import id2url

from weboob.capabilities.paste import PasteNotFound

from .pages import PastePage, PostPage
from .paste import PastebinPaste

import urllib
import re

__all__ = ['PastebinBrowser']

class BadAPIRequest(Exception):
    pass


class PastebinBrowser(BaseBrowser):
    DOMAIN = 'pastebin.com'
    ENCODING = 'UTF-8'
    PASTE_URL = 'http://%s/(?P<id>.+)' % DOMAIN
    API_URL = 'http://%s/api/api_post.php' % DOMAIN
    PAGES = {PASTE_URL: PastePage,
            'http://%s/' % DOMAIN: PostPage}

    def fill_paste(self, paste):
        """
        Get as much as information possible from the paste page
        """
        try:
            self.location(paste.page_url)
            return self.page.fill_paste(paste)
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    @id2url(PastebinPaste.id2url)
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

    def post_paste(self, paste):
        self.home()
        self.page.post(paste)
        paste.id = self.page.get_id()

    def api_post_paste(self, dev_key, paste):
        data = {'api_dev_key': dev_key,
                'api_option': 'paste',
                'api_paste_expire_date': '1M',
                'api_paste_code': paste.contents.encode(self.ENCODING),
        }
        if paste.title:
            data['api_paste_name'] = paste.title.encode(self.ENCODING)
        res = self.readurl(self.API_URL, urllib.urlencode(data)).decode(self.ENCODING)
        self._validate_api_response(res)
        paste.id = re.match('^%s$' % self.PASTE_URL, res).groupdict()['id']

    def _validate_api_response(self, res):
        matches = re.match('Bad API request, (?P<error>.+)', res)
        if matches:
            raise BadAPIRequest(matches.groupdict().get('error'))

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

from mechanize import RobustFactory
import re

from weboob.tools.browser import BaseBrowser, BrowserUnavailable, BrowserHTTPNotFound

from weboob.capabilities.paste import PasteNotFound
from weboob.tools.browser.decorators import id2url, check_url

from .pages import PastePage, CaptchaPage, PostPage
from .paste import PastealaconPaste

__all__ = ['PastealaconBrowser']


class PastealaconBrowser(BaseBrowser):
    DOMAIN = 'pastealacon.com'
    ENCODING = 'ISO-8859-1'
    PASTE_URL = 'http://%s/(?P<id>\d+)' % DOMAIN
    PAGES = {PASTE_URL: PastePage,
             'http://%s/%s' % (DOMAIN, re.escape('pastebin.php?captcha=1')): CaptchaPage,
             'http://%s/' % DOMAIN: PostPage}

    def __init__(self, *args, **kwargs):
        kwargs['factory'] = RobustFactory()
        BaseBrowser.__init__(self, *args, **kwargs)

    @id2url(PastealaconPaste.id2url)
    @check_url(PASTE_URL)
    def get_paste(self, url):
        _id = re.match('^%s$' % self.PASTE_URL, url).groupdict()['id']
        return PastealaconPaste(_id)

    def fill_paste(self, paste):
        """
        Get as much as information possible from the paste page
        """
        self.location(paste.page_url)
        return self.page.fill_paste(paste)

    def get_contents(self, _id):
        """
        Get the contents from the raw URL
        This is the fastest and safest method if you only want the content.
        Returns unicode.
        """
        try:
            return self.readurl('http://%s/pastebin.php?dl=%s' % (self.DOMAIN, _id), if_fail='raise').decode(self.ENCODING)
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    def post_paste(self, paste, expiration=None):
        self.home()
        self.page.post(paste, expiration=expiration)
        if self.is_on_page(CaptchaPage):
            raise BrowserUnavailable("Detected as spam and unable to handle the captcha")
        paste.id = self.page.get_id()

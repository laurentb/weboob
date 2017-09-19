# -*- coding: utf-8 -*-

# Copyright(C) 2011-2014 Laurent Bachelier
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

from weboob.capabilities.paste import BasePaste, PasteNotFound
from weboob.browser.filters.standard import BrowserURL, CleanText, DateTime, Env, Field, RawText, Regexp
from weboob.browser.pages import HTMLPage
from weboob.browser.browsers import PagesBrowser
from weboob.browser.url import URL
from weboob.browser.elements import ItemElement, method
from weboob.exceptions import BrowserHTTPNotFound


class Spam(Exception):
    def __init__(self):
        super(Spam, self).__init__("Detected as spam and unable to handle the captcha")


class PastealaconPaste(BasePaste):
    # all pastes are public
    public = True

    # TODO perhaps move this logic elsewhere, remove this and id2url from capability
    # (page_url is required by pastoob)
    @property
    def page_url(self):
        return self.url


class PastePage(HTMLPage):
    @method
    class fill_paste(ItemElement):
        klass = PastealaconPaste

        obj_id = Env('id')
        obj_title = Regexp(CleanText('id("content")/h3'), r'Posted by (.+) on .+ \(')
        obj__date = DateTime(Regexp(CleanText('id("content")/h3'), r'Posted by .+ on (.+) \('))
        obj_contents = RawText('//textarea[@id="code"]')
        obj_url = BrowserURL('paste', id=Field('id'))

        def parse(self, el):
            # there is no 404, try to detect if there really is a content
            if len(el.xpath('id("content")/div[@class="syntax"]//ol')) != 1:
                raise PasteNotFound()


class CaptchaPage(HTMLPage):
    pass


class PostPage(HTMLPage):
    def post(self, paste, expiration=None):
        form = self.get_form(name='editor')
        form['code2'] = paste.contents
        form['poster'] = paste.title
        if expiration:
            form['expiry'] = expiration
        form.submit()


class PastealaconBrowser(PagesBrowser):
    BASEURL = 'http://paste.alacon.org/'

    paste = URL(r'(?P<id>\d+)', PastePage)
    captcha = URL(r'%s' % re.escape('pastebin.php?captcha=1'), CaptchaPage)
    raw = URL(r'%s(?P<id>\d+)' % re.escape('pastebin.php?dl='))
    post = URL(r'$', PostPage)

    @paste.id2url
    def get_paste(self, url):
        url = self.absurl(url, base=True)
        m = self.paste.match(url)
        if m:
            return PastealaconPaste(m.groupdict()['id'])

    def fill_paste(self, paste):
        """
        Get as much as information possible from the paste page
        """
        self.paste.stay_or_go(id=paste.id)
        return self.page.fill_paste(paste)

    def get_contents(self, _id):
        """
        Get the contents from the raw URL
        This is the fastest and safest method if you only want the content.
        Returns unicode.
        """
        try:
            # despite what the HTTP header says, it is iso8859
            return self.raw.open(id=_id).content.decode('iso8859-15')
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    def post_paste(self, paste, expiration=None):
        self.post.stay_or_go().post(paste, expiration=expiration)
        if self.captcha.is_here():
            raise Spam()
        self.page.fill_paste(paste)

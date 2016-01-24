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

from urlparse import urljoin

from weboob.capabilities.paste import BasePaste, PasteNotFound
from weboob.browser.filters.standard import CleanText, DateTime, Env, RawText, Regexp
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

    @property
    def page_url(self):
        return urljoin(PastealaconBrowser.BASEURL, self.id)


class PastePage(HTMLPage):
    @method
    class fill_paste(ItemElement):
        klass = PastealaconPaste

        obj_id = Env('id')
        obj_title = Regexp(CleanText('id("content")/h3'), r'Posted by (.+) on .+ \(')
        obj__date = DateTime(Regexp(CleanText('id("content")/h3'), r'Posted by .+ on (.+) \('))
        obj_contents = RawText('//textarea[@id="code"]')

        def obj__baseurl(self):
            return self.page.browser.BASEURL

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
    VERIFY = False

    paste = URL(r'(?P<id>\d+)', r'\?show=(?P<id>[0-9a-z]+)', PastePage)
    captcha = URL(r'pastebin\.php\?captcha=1', CaptchaPage)
    raw = URL(r'pastebin\.php\?dl=(?P<id>\d+)', r'\?dl=(?P<id>[a-z0-9]+)')
    post = URL(r'$', PostPage)

    def __init__(self, baseurl, *args, **kwargs):
        self.BASEURL = baseurl
        super(PastealaconBrowser, self).__init__(*args, **kwargs)

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
        assert self.paste.is_here()
        return self.page.fill_paste(paste)

    def get_contents(self, _id):
        """
        Get the contents from the raw URL
        This is the fastest and safest method if you only want the content.
        Returns unicode.
        """
        try:
            return self.raw.open(id=_id).text
        except BrowserHTTPNotFound:
            raise PasteNotFound()

    def post_paste(self, paste, expiration=None):
        self.post.stay_or_go()
        import code; code.interact(local=locals())
        assert self.post.is_here()
        self.page.post(paste, expiration=expiration)
        if self.captcha.is_here():
            raise Spam()
        self.page.fill_paste(paste)

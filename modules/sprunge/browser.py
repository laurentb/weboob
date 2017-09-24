# -*- coding: utf-8 -*-

# Copyright(C) 2017 Laurent Bachelier
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

from weboob.browser.browsers import PagesBrowser
from weboob.browser.elements import ItemElement, method
from weboob.browser.filters.standard import BrowserURL, Env, Field
from weboob.browser.pages import HTMLPage
from weboob.browser.url import URL
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.paste import BasePaste, PasteNotFound


class SprungePaste(BasePaste):
    # all pastes are private
    public = False

    # TODO perhaps move this logic elsewhere, remove this and id2url from capability
    # (page_url is required by pastoob)
    @property
    def page_url(self):
        return self.url


class PastePage(HTMLPage):
    @method
    class fill_paste(ItemElement):
        klass = SprungePaste

        obj_id = Env('id')
        obj_title = NotAvailable

        def obj_contents(self):
            text = self.page.response.text
            # Sprunge seems to add a newline to our original text
            if text.endswith(u'\n'):
                text = text[:-1]
            return text

        obj_url = BrowserURL('paste', id=Field('id'))

        def validate(self, obj):
            if obj.contents == u'%s not found.' % obj.id:
                raise PasteNotFound()
            return True


class SprungeBrowser(PagesBrowser):
    BASEURL = 'http://sprunge.us/'

    paste = URL(r'(?P<id>\w+)', PastePage)
    post = URL(r'$')

    @paste.id2url
    def get_paste(self, url):
        url = self.absurl(url, base=True)
        m = self.paste.match(url)
        if m:
            return SprungePaste(m.groupdict()['id'])

    def fill_paste(self, paste):
        """
        Get as much as information possible from the paste page
        """
        return self.paste.stay_or_go(id=paste.id).fill_paste(paste)

    def post_paste(self, paste):
        url = self.post.open(data={'sprunge': paste.contents}).text.strip()
        self.location(url)
        return self.page.fill_paste(paste)

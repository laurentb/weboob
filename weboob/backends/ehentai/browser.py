# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Roger Philibert
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

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from urllib import urlencode

from .pages import IndexPage, GalleryPage, ImagePage, HomePage, LoginPage
from .gallery import EHentaiImage


__all__ = ['EHentaiBrowser']


class EHentaiBrowser(BaseBrowser):
    ENCODING = None
    PAGES = {
            r'http://[^/]+/': IndexPage,
            r'http://[^/]+/\?.*': IndexPage,
            r'http://[^/]+/g/.+': GalleryPage,
            r'http://[^/]+/s/.*': ImagePage,
            r'http://[^/]+/home\.php': HomePage,
            r'http://e-hentai\.org/bounce_login\.php': LoginPage,
            }

    def __init__(self, domain, username, password, *args, **kwargs):
        self.DOMAIN = domain
        self.logged = False
        BaseBrowser.__init__(self, *args, **kwargs)
        if password is not None:
            self.login(username, password)

    def _gallery_page(self, gallery, n):
        return gallery.url + ('?p=%d' % n)

    def iter_search_results(self, pattern):
        self.location(self.buildurl('/', f_search=pattern))
        assert self.is_on_page(IndexPage)
        return self.page.iter_galleries()

    def iter_gallery_images(self, gallery):
        self.location(gallery.url)
        assert self.is_on_page(GalleryPage)
        i = 0
        while True:
            n = self.page._next_page_link();

            for img in self.page.image_pages():
                yield EHentaiImage(img)

            if n is None:
                break

            i += 1
            self.location(self._gallery_page(gallery, i))
            assert self.is_on_page(GalleryPage)

    def get_image_url(self, image):
        self.location(image.id)
        assert self.is_on_page(ImagePage)
        return self.page.get_url()
    
    def fill_gallery(self, gallery, fields):
        self.location(gallery.id)
        assert self.is_on_page(GalleryPage)
        gallery.url = gallery.id
        self.page.fill_gallery(gallery)

    def login(self, username, password):
        assert isinstance(username, basestring)
        assert isinstance(password, basestring)

        data = {'ipb_login_username': username,
                'ipb_login_password': password}
        self.location('http://e-hentai.org/bounce_login.php', urlencode(data), no_login=True)

        assert self.is_on_page(LoginPage)
        if not self.page.is_logged():
            raise BrowserIncorrectPassword()

        # necessary in order to reach the fjords
        self.home()


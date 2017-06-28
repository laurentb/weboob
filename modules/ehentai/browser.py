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

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.tools.compat import urlencode

from .pages import IndexPage, GalleryPage, ImagePage, HomePage, LoginPage
from .gallery import EHentaiImage


__all__ = ['EHentaiBrowser']


class EHentaiBrowser(Browser):
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
        Browser.__init__(self, parser=('lxmlsoup',), *args, **kwargs)
        if password:
            self.login(username, password)

    def _gallery_url(self, gallery):
        return 'http://%s/g/%s/' % (self.DOMAIN, gallery.id)

    def _gallery_page(self, gallery, n):
        return gallery.url + ('?p='+str(n))

    def search_galleries(self, pattern):
        self.location(self.buildurl('/', f_search=pattern.encode('utf-8')))
        assert self.is_on_page(IndexPage)
        return self.page.iter_galleries()

    def latest_gallery(self):
        self.location('/')
        assert self.is_on_page(IndexPage)
        return self.page.iter_galleries()

    def iter_gallery_images(self, gallery):
        self.location(gallery.url)
        assert self.is_on_page(GalleryPage)
        for n in self.page._page_numbers():
            self.location(self._gallery_page(gallery, n))
            assert self.is_on_page(GalleryPage)

            for img in self.page.image_pages():
                yield EHentaiImage(img)

    def get_image_url(self, image):
        self.location(image.id)
        assert self.is_on_page(ImagePage)
        return self.page.get_url()

    def gallery_exists(self, gallery):
        gallery.url = self._gallery_url(gallery)
        self.location(gallery.url)
        assert self.is_on_page(GalleryPage)
        return self.page.gallery_exists(gallery)

    def fill_gallery(self, gallery, fields):
        gallery.url = self._gallery_url(gallery)
        self.location(gallery.url)
        assert self.is_on_page(GalleryPage)
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

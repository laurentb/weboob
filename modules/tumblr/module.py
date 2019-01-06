# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.browser.exceptions import ClientError, HTTPNotFound
from weboob.capabilities.gallery import CapGallery, BaseGallery, BaseImage, Thumbnail
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.compat import urlparse
from weboob.tools.value import Value

from .browser import TumblrBrowser


__all__ = ['TumblrModule']


class TumblrModule(Module, CapGallery):
    NAME = 'tumblr'
    DESCRIPTION = 'images in tumblr blogs'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    CONFIG = BackendConfig(Value('url', label='URL of the tumblr', regexp='https?://.+'))

    BROWSER = TumblrBrowser

    def create_default_browser(self):
        return self.create_browser(self.url())

    def url(self):
        return self.config['url'].get()

    def get_gallery(self, _id):
        title, icon = self.browser.get_title_icon()
        if icon:
            icon = Thumbnail(icon)
        return BaseGallery(_id, title=title, url=self.url(), thumbnail=icon)

    def search_galleries(self, pattern, sortby=CapGallery.SEARCH_RELEVANCE):
        pattern = pattern.lower()
        url = self.url()
        if pattern in url or pattern in self.browser.get_title_icon()[0].lower():
            yield self.get_gallery(urlparse(url).netloc)

    def iter_gallery_images(self, gallery):
        for img in self.browser.iter_images(gallery):
            yield img

    def fill_img(self, img, fields):
        if 'data' in fields:
            try:
                img.data = self.browser.open(img.url).content
            except (ClientError, HTTPNotFound):
                img.data = b''
        if 'thumbnail' in fields and img.thumbnail:
            self.fill_img(img.thumbnail, ('data',))

    OBJECTS = {
        BaseImage: fill_img,
        BaseGallery: fill_img,
    }

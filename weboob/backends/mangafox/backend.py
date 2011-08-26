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

from __future__ import with_statement

import re

from weboob.capabilities.gallery import ICapGallery, BaseGallery, BaseImage
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser, BasePage

__all__ = ['MangafoxBackend']

class DisplayPage(BasePage):
    def get_page(self, gallery):
        src = self.document.xpath("//img[@id='image']/attribute::src")[0]

        return BaseImage(src,
                gallery=gallery,
                url=src)

    def page_list(self):
        l = self.document.xpath("//select[@onchange='change_page(this)']")[0]
        l = l.xpath("./option/@value")
        return l

class MangafoxBrowser(BaseBrowser):
    PAGES = { r'http://.+\.mangafox.\w+/manga/[^/]+/[^/]+/([^/]+/)?.+\.html': DisplayPage }

    def iter_gallery_images(self, gallery):
        self.location(gallery.url)
        assert self.is_on_page(DisplayPage)

        for p in self.page.page_list():
            self.location('%s.html' % p)
            assert self.is_on_page(DisplayPage)
            yield self.page.get_page(gallery)

    def fill_image(self, image, fields):
        if 'data' in fields:
            image.data = self.readurl(image.url)

class MangafoxBackend(BaseBackend, ICapGallery):
    NAME = 'mangafox'
    MAINTAINER = 'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '0.9'
    DESCRIPTION = 'Mangafox'
    LICENSE = 'AGPLv3+'
    BROWSER = MangafoxBrowser

    def iter_gallery_images(self, gallery):
        with self.browser:
            return self.browser.iter_gallery_images(gallery)

    def get_gallery(self, _id):
        match = re.match(r'(?:(?:.+mangafox.com/manga)?/)?([^/]+/[^/]+(?:/[^/]+)?)', _id)
        if match is None:
            return None

        _id = match.group(1)

        gallery = BaseGallery(_id, url=('http://www.mangafox.com/manga/%s' % _id))
        with self.browser:
            return gallery

    def fill_gallery(self, gallery, fields):
        gallery.title = gallery.id

    def fill_image(self, image, fields):
        with self.browser:
            self.browser.fill_image(image, fields)

    OBJECTS = {
            BaseGallery: fill_gallery,
            BaseImage: fill_image }

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


import re

from weboob.capabilities.gallery import CapGallery, BaseGallery, BaseImage
from weboob.tools.json import json
from weboob.tools.backend import Module
from weboob.deprecated.browser import Browser, Page

__all__ = ['IzneoModule']


class ReaderV2(Page):
    def get_ean(self):
        return self.document.xpath("//div[@id='viewer']/attribute::rel")[0]

    def iter_gallery_images(self, gallery):
        ean = self.get_ean()
        pages = json.load(self.browser.openurl(
            'http://www.izneo.com/playerv2/ajax.php?ean=%s&action=get_list_jpg'
            % ean))

        for page in pages['list']:
            width = 1200  # maximum width
            yield BaseImage(page['page'],
                    gallery=gallery,
                    url=("http://www.izneo.com/playerv2/%s/%s/%s/%d/%s" %
                        (page['expires'], page['token'], ean, width, page['page'])))


class IzneoBrowser(Browser):
    PAGES = {r'http://.+\.izneo.\w+/readv2-.+': ReaderV2}

    def iter_gallery_images(self, gallery):
        self.location(gallery.url)
        assert self.is_on_page(ReaderV2)
        return self.page.iter_gallery_images(gallery)

    def fill_image(self, image, fields):
        if 'data' in fields:
            image.data = self.readurl(self.request_class(
                image.url, None, {'Referer': image.gallery.url}))


class IzneoModule(Module, CapGallery):
    NAME = 'izneo'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '1.4'
    DESCRIPTION = 'Izneo digital comics'
    LICENSE = 'AGPLv3+'
    BROWSER = IzneoBrowser

    def iter_gallery_images(self, gallery):
        with self.browser:
            return self.browser.iter_gallery_images(gallery)

    def get_gallery(self, _id):
        match = re.match(r'(?:(?:.+izneo.com/)?readv2-)?(\d+-\d+)/?$', _id)
        if match is None:
            return None

        _id = match.group(1)

        gallery = BaseGallery(_id, url=('http://www.izneo.com/readv2-%s' % _id))
        with self.browser:
            return gallery

    def fill_gallery(self, gallery, fields):
        gallery.title = gallery.id

    def fill_image(self, image, fields):
        with self.browser:
            self.browser.fill_image(image, fields)

    OBJECTS = {
            BaseGallery: fill_gallery,
            BaseImage: fill_image}

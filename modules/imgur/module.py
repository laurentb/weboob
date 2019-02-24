# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import re
from base64 import b64encode

from weboob.capabilities.base import StringField
from weboob.capabilities.gallery import BaseGallery, BaseImage, CapGallery
from weboob.capabilities.image import CapImage, Thumbnail
from weboob.capabilities.paste import BasePaste, CapPaste
from weboob.tools.backend import Module
from weboob.tools.capabilities.paste import image_mime
from weboob.tools.date import datetime

from .browser import ImgurBrowser

__all__ = ['ImgurModule']


class ImgPaste(BasePaste):
    delete_url = StringField('URL to delete the image')

    @classmethod
    def id2url(cls, id):
        return 'https://imgur.com/%s' % id

    @property
    def raw_url(self):
        # TODO get the right extension
        return 'https://i.imgur.com/%s.png' % self.id


class Img(BaseImage):
    @property
    def thumbnail_url(self):
        return ImgPaste(self.id + 't').raw_url

    @property
    def raw_url(self):
        return 'https://i.imgur.com/%s.%s' % (self.id, self.ext)


class ImgGallery(BaseGallery):
    def __init__(self, *args, **kwargs):
        super(ImgGallery, self).__init__(*args, **kwargs)
        self._imgs = []

    @classmethod
    def id2url(cls, id):
        return 'https://imgur.com/gallery/%s' % id

    def iter_image(self):
        return self._imgs


class ImgurModule(Module, CapPaste, CapGallery, CapImage):
    NAME = 'imgur'
    DESCRIPTION = u'imgur image upload service'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = ImgurBrowser

    IMGURL = re.compile(r'https?://(?:[a-z]+\.)?imgur.com/([a-zA-Z0-9]+)(?:\.[a-z]+)?$')
    GALLURL = re.compile(r'https?://(?:[a-z]+\.)?imgur.com/a/([a-zA-Z0-9]+)/?$')
    ID = re.compile(r'[0-9a-zA-Z]+$')

    # CapPaste
    def new_paste(self, *a, **kw):
        return ImgPaste(*a, **kw)

    def can_post(self, contents, title=None, public=None, max_age=None):
        if public is False:
            return 0
        elif re.search(r'[^a-zA-Z0-9=+/\s]', contents):
            return 0
        elif max_age:
            return 0
        else:
            mime = image_mime(contents, ('gif', 'jpeg', 'png', 'tiff', 'xcf', 'pdf'))
            return 20 * int(mime is not None)

    def get_paste(self, id):
        mtc = self.IMGURL.match(id)
        if mtc:
            id = mtc.group(1)
        elif not self.ID.match(id):
            return None

        paste = ImgPaste(id)
        bin = self.browser.open_raw(paste.raw_url).content
        paste.contents = b64encode(bin)
        return paste

    def post_paste(self, paste, max_age=None):
        res = self.browser.post_image(b64=paste.contents, title=paste.title)
        paste.id = res['id']
        paste.delete_url = res['delete_url']
        return paste

    # CapGallery
    def _build_img(self, d, n, gallery):
        img = Img(d['id'], gallery=gallery, url=d['link'], index=n)
        img.title = d['title'] or u''
        img.description = d['description'] or u''
        img.ext = img.url.rsplit('.', 1)[-1]
        img.date = datetime.fromtimestamp(d['datetime'])
        img.thumbnail = Thumbnail(img.thumbnail_url)
        img.thumbnail.date = img.date
        img.nsfw = bool(d['nsfw'])
        img.size = d['size']
        return img

    def _build_gallery(self, d):
        gallery = ImgGallery(d['id'], url=d['link'])
        gallery.title = d['title'] or u''
        gallery.description = d['description'] or u''
        gallery.date = datetime.fromtimestamp(d['datetime'])
        gallery.thumbnail = Thumbnail(Img(d['cover']).thumbnail_url)

        if 'images' in d:
            for n, d in enumerate(d['images']):
                img = self._build_img(d, n, gallery)
                gallery._imgs.append(img)
            gallery.cardinality = len(gallery._imgs)

        return gallery

    def get_gallery(self, id):
        mtc = self.GALLURL.match(id)
        if mtc:
            id = mtc.group(1)
        elif not self.ID.match(id):
            return None

        d = self.browser.get_gallery(id)
        if d is None:
            return None
        return self._build_gallery(d)

    def iter_gallery_images(self, gallery):
        if not len(gallery._imgs):
            new = self.get_gallery(gallery.id)
            gallery._imgs = new._imgs
        return gallery._imgs

    def search_galleries(self, pattern, sortby=CapGallery.SEARCH_RELEVANCE):
        d = self.browser.search_items(pattern, sortby)
        for sub in d:
            if sub['is_album']:
                yield self._build_gallery(sub)

    # CapImage
    def get_file(self, id):
        mtc = self.IMGURL.match(id)
        if mtc:
            id = mtc.group(1)
        elif not self.ID.match(id):
            return None

        d = self.browser.get_image(id)
        if d is None:
            return None
        return self._build_img(d, 0, None)

    def search_file(self, pattern, sortby=CapGallery.SEARCH_RELEVANCE):
        d = self.browser.search_items(pattern, sortby)
        for sub in d:
            if not sub['is_album']:
                yield self._build_img(sub, 0, None)

    def search_image(self, pattern, sortby=CapGallery.SEARCH_RELEVANCE, nsfw=False):
        for img in self.search_file(pattern, sortby):
            if nsfw or not img.nsfw:
                yield img

    def fill_img(self, img, fields):
        if 'data' in fields:
            self.browser.fill_file(img, fields)
        if 'thumbnail' in fields and img.thumbnail:
            self.fillobj(img.thumbnail, None)
        return img

    OBJECTS = {Img: fill_img, Thumbnail: fill_img, BaseGallery: fill_img}

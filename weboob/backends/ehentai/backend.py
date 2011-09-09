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
from weboob.capabilities.gallery import ICapGallery
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.misc import ratelimit
from weboob.tools.value import Value, ValueBackendPassword

from .browser import EHentaiBrowser
from .gallery import EHentaiGallery, EHentaiImage


__all__ = ['EHentaiBackend']


class EHentaiBackend(BaseBackend, ICapGallery):
    NAME = 'ehentai'
    MAINTAINER = 'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '0.9'
    DESCRIPTION = 'E-hentai galleries'
    LICENSE = 'AGPLv3+'
    BROWSER = EHentaiBrowser
    CONFIG = BackendConfig(
        Value('domain', label='Domain', default='g.e-hentai.org'),
        Value('username', label='Username', default=''),
        ValueBackendPassword('password', label='Password'))

    def create_default_browser(self):
        username = self.config['username'].get()
        if username:
            password = self.config['password'].get()
        else:
            password = None
        return self.create_browser(self.config['domain'].get(), username, password)

    def iter_search_results(self, pattern=None, sortby=None, max_results=None):
        with self.browser:
            return self.browser.iter_search_results(pattern)

    def iter_gallery_images(self, gallery):
        self.fillobj(gallery, ('url',))
        with self.browser:
            return self.browser.iter_gallery_images(gallery)

    ID_REGEXP = r'/?\d+/[\dabcdef]+/?'
    URL_REGEXP = r'.+/g/(%s)' % ID_REGEXP
    def get_gallery(self, _id):
        match = re.match(r'^%s$' % self.URL_REGEXP, _id)
        if match:
            _id = match.group(1)
        else:
            match = re.match(r'^%s$' % self.ID_REGEXP, _id)
            if match:
                _id = match.group(0)
            else:
                return None
        
        gallery = EHentaiGallery(_id)
        with self.browser:
            if self.browser.gallery_exists(gallery):
                return gallery
            else:
                return None

    def fill_gallery(self, gallery, fields):
        if not gallery.__iscomplete__():
            with self.browser:
                self.browser.fill_gallery(gallery, fields)

    def fill_image(self, image, fields):
        with self.browser:
            image.url = self.browser.get_image_url(image)
            if 'data' in fields:
                ratelimit("ehentai_get", 2)
                image.data = self.browser.readurl(image.url)

    OBJECTS = {
            EHentaiGallery: fill_gallery,
            EHentaiImage: fill_image }

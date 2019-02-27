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


from weboob.capabilities.image import CapImage, BaseImage, Thumbnail
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .browser import PixabayBrowser


__all__ = ['PixabayModule']


class Img(BaseImage):
    def __init__(self, *args):
        super(Img, self).__init__(*args)
        self._page_url = None

    @classmethod
    def id2url(cls, id):
        pass

    @property
    def page_url(self):
        return self._page_url


class PixabayModule(Module, CapImage):
    NAME = 'pixabay'
    DESCRIPTION = u'Pixabay public domain photo search'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'

    BROWSER = PixabayBrowser

    CONFIG = BackendConfig(Value('username',                label='Username (only for full-size images)', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           ValueBackendPassword('api_key',  label='API key (optional)', default='', noprompt=True))

    def create_default_browser(self):
        key = self.config['api_key'].get()
        username = self.config['username'].get()
        if username:
            return self.BROWSER(key, username,
                                self.config['password'].get())
        else:
            return self.BROWSER(key, None, None)

    def get_file(self, _id):
        return self.get_image(_id)

    def _build_image(self, d):
        img = Img(unicode(d['id']))
        img.title = d['tags']
        img.author = d['user']
        img.thumbnail = Thumbnail(d['previewURL'])
        img.url = d['webformatURL']
        img._page_url = d['pageURL']
        img.license = u'Public Domain'
        return img

    def get_image(self, _id):
        d = self.browser.get_image(_id)
        if d:
            return self._build_image(d)

    def search_file(self, pattern, sortby=0):
        return self.search_image(pattern, sortby)

    def has_login(self):
        return self.browser.username and self.browser.password

    def search_image(self, pattern, sortby=0, nsfw=False):
        for d in self.browser.search_images(pattern, sortby, nsfw):
            yield self._build_image(d)

    def fill_img(self, obj, fields):
        if 'data' in fields:
            if self.has_login():
                obj.data = self.browser.download_image(obj.page_url)
            else:
                obj.data = self.browser.open(obj.url).content
        if 'thumbnail' in fields:
            if not obj.thumbnail.data:
                obj.thumbnail.data = self.browser.open(obj.thumbnail.url).content
        return obj

    def fill_thumb(self, obj, fields):
        if 'data' in fields:
            obj.data = self.browser.open(obj.url).content
        return obj

    OBJECTS = {Img: fill_img, Thumbnail: fill_thumb}

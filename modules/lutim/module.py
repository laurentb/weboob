# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
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

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.paste import CapPaste, BasePaste
from weboob.tools.capabilities.paste import image_mime
from weboob.tools.compat import urljoin
from weboob.tools.value import Value

from .browser import LutimBrowser


__all__ = ['LutimModule']


class LutimModule(Module, CapPaste):
    NAME = 'lutim'
    DESCRIPTION = u'lutim website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = LutimBrowser

    CONFIG = BackendConfig(Value('base_url', label='Hoster base URL', default='https://lut.im/'))

    @property
    def base_url(self):
        url = self.config['base_url'].get()
        if not url.endswith('/'):
            url = url + '/'
        return url

    def create_default_browser(self):
        return self.create_browser(self.base_url)

    def can_post(self, contents, title=None, public=None, max_age=None):
        if public:
            return 0
        elif max_age and max_age < 86400:
            return 0 # it cannot be shorter than one day
        elif re.search(r'[^a-zA-Z0-9=+/\s]', contents):
            return 0 # not base64, thus not binary
        else:
            mime = image_mime(contents, ('gif', 'jpeg', 'png'))
            return 20 * int(mime is not None)

    def get_paste(self, url):
        if not url.startswith('http'):
            url = urljoin(self.base_url, url)
        paste = self.new_paste(url)
        self.browser.fetch(paste)
        return paste

    def new_paste(self, _id):
        paste = LutimPaste(_id)
        return paste

    def post_paste(self, paste, max_age):
        return self.browser.post(paste, max_age)


class LutimPaste(BasePaste):
    @classmethod
    def id2url(cls, id):
        return id

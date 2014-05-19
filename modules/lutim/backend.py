# -*- coding: utf-8 -*-

# Copyright(C) 2014      Vincent A
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


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.capabilities.paste import ICapPaste, BasePaste
from weboob.tools.capabilities.paste import image_mime
from weboob.tools.value import Value
import re
from urlparse import urljoin

from .browser import LutimBrowser


__all__ = ['LutimBackend']


class LutimBackend(BaseBackend, ICapPaste):
    NAME = 'lutim'
    DESCRIPTION = u'LUTIm website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '0.j'

    BROWSER = LutimBrowser

    CONFIG = BackendConfig(Value('base_url', label='Hoster base URL', default='http://lut.im/'))

    def _base_url(self):
        url = self.config['base_url'].get()
        if not url.endswith('/'):
            url = url + '/'
        return url

    def create_default_browser(self):
        return self.create_browser(self._base_url())

    def can_post(self, contents, title=None, public=None, max_age=None):
        if re.search(r'[^a-zA-Z0-9=+/\s]', contents):
            return 0
        elif max_age and max_age < 86400:
            return 0 # it cannot be shorter than one day
        else:
            mime = image_mime(contents, ('gif', 'jpeg', 'png'))
            return 20 * int(mime is not None)

    def new_paste(self, *a, **kw):
        base_url = self._base_url()

        class LutImage(BasePaste):
            @classmethod
            def id2url(cls, id):
                return urljoin(base_url, id)

            @classmethod
            def url2id(cls, url):
                if url.startswith(base_url):
                    return url[len(base_url):]

        return LutImage(*a, **kw)

    def get_paste(self, id):
        paste = self.new_paste(id)

        if '/' in id:
            paste.id = paste.url2id(id)
            if not paste.id:
                return None

        response = self.browser.readurl(paste.page_url)
        if response:
            paste.contents = response.encode('base64')
            return paste

    def post_paste(self, paste, max_age=None):
        d = self.browser.post(paste.title or None, paste.contents.decode('base64'), (max_age or 0) // 86400)
        if d:
            paste.id = d['id']

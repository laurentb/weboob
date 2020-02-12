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

from base64 import b64decode

from weboob.capabilities.paste import CapPaste, BasePaste
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.capabilities.paste import bin_to_b64
from weboob.tools.value import Value

from .browser import JirafeauBrowser


__all__ = ['JirafeauModule']


class JirafeauPaste(BasePaste):
    @property
    def page_url(self):
        return self.url


class JirafeauModule(Module, CapPaste):
    NAME = 'jirafeau'
    DESCRIPTION = u'Jirafeau-based file upload website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    CONFIG = BackendConfig(Value('base_url', label='Base Jirafeau URL',
                                 description='URL of the Jirafeau-based site to use',
                                 regexp=r'https?://.*',
                                 default='https://jirafeau.net/'))

    BROWSER = JirafeauBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['base_url'].get())

    def can_post(self, contents, title=None, public=None, max_age=None):
        if public or max_age not in self.browser.age_keyword:
            return 0

        max_size, _ = self.browser.get_max_sizes()
        if max_size and len(b64decode(contents)) > max_size:
            return 0
        return 1

    def get_paste(self, url):
        d = self.browser.recognize(url)
        if not d:
            return
        if self.browser.exists(d['id']):
            return

        ret = JirafeauPaste(d['id'])
        ret.url = d['url']
        return ret

    def new_paste(self, *args, **kwargs):
        return JirafeauPaste(*args, **kwargs)

    def post_paste(self, paste, max_age=None):
        d = self.browser.post(b64decode(paste.contents), paste.title, max_age)
        paste.id = d['id']
        paste.url = d['page_url']
        return paste

    def fill_paste(self, obj, fields):
        if 'contents' in fields:
            data = self.browser.download(obj.id)
            obj.contents = bin_to_b64(data)

    OBJECTS = {JirafeauPaste: fill_paste}

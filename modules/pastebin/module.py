# -*- coding: utf-8 -*-

# Copyright(C) 2011-2014 Laurent Bachelier
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


from weboob.capabilities.base import NotLoaded
from weboob.tools.backend import BackendConfig, Module
from weboob.tools.capabilities.paste import BasePasteModule
from weboob.tools.value import Value, ValueBackendPassword

from .browser import PastebinBrowser, PastebinPaste


class PastebinModule(Module, BasePasteModule):
    NAME = 'pastebin'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '1.5'
    DESCRIPTION = 'Pastebin text sharing service'
    LICENSE = 'AGPLv3+'
    BROWSER = PastebinBrowser
    CONFIG = BackendConfig(
        Value('username', label='Optional username', default=''),
        ValueBackendPassword('password', label='Optional password', default=''),
        ValueBackendPassword('api_key',  label='Optional API key',  default='', noprompt=True),
    )

    EXPIRATIONS = {
        600: '10M',
        3600: '1H',
        3600 * 24: '1D',
        3600 * 24 * 30: '1M',
        False: 'N',
    }

    def create_default_browser(self):
        username = self.config['username'].get()
        if username:
            password = self.config['password'].get()
        else:
            password = None
        return self.create_browser(self.config['api_key'].get() or None,
                                   username, password)

    def new_paste(self, *args, **kwargs):
        return PastebinPaste(*args, **kwargs)

    def can_post(self, contents, title=None, public=None, max_age=None):
        if max_age is not None:
            if self.get_closest_expiration(max_age) is None:
                return 0
        if not title or len(title) <= 60:
            return 2
        return 1

    def get_paste(self, _id):
        return self.browser.get_paste(_id)

    def fill_paste(self, paste, fields):
        # if we only want the contents
        if fields == ['contents']:
            if paste.contents is NotLoaded:
                paste.contents = self.browser.get_contents(paste.id)
        # get all fields
        elif fields is None or len(fields):
            self.browser.fill_paste(paste)
        return paste

    def post_paste(self, paste, max_age=None, use_api=True):
        if max_age is not None:
            expiration = self.get_closest_expiration(max_age)
        else:
            expiration = None
        if use_api and self.config.get('api_key').get():
            self.browser.api_post_paste(paste, expiration=self.EXPIRATIONS.get(expiration))
        else:
            self.browser.post_paste(paste, expiration=self.EXPIRATIONS.get(expiration))

    OBJECTS = {PastebinPaste: fill_paste}

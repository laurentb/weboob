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


from weboob.tools.backend import Module
from weboob.capabilities.paste import BasePaste
from weboob.tools.capabilities.paste import BasePasteModule
from weboob.tools.capabilities.paste import image_mime
from weboob.deprecated.browser.decorators import check_url
import re

from .browser import UnseeBrowser


__all__ = ['UnseeModule']


class UnPaste(BasePaste):
    @classmethod
    def id2url(cls, id):
        return 'https://unsee.cc/%s' % id


class UnseeModule(Module, BasePasteModule):
    NAME = 'unsee'
    DESCRIPTION = u'unsee.cc expiring image hosting'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = UnseeBrowser

    EXPIRATIONS = {3600: 'hour', 86400: 'day', 86400 * 7: 'week'}

    def can_post(self, contents, title=None, public=None, max_age=None):
        if re.search(r'[^a-zA-Z0-9=+/\s]', contents):
            return 0
        elif max_age is not None and not self.get_closest_expiration(max_age):
            return 0
        else:
            mime = image_mime(contents, ('gif', 'jpeg', 'png'))
            return 20 * int(mime is not None)

    @check_url('https?://unsee.cc/.+')
    def get_paste(self, id):
        paste = UnPaste(id)
        paste.contents = self.browser.get_image(id).encode('base64')
        return paste

    def new_paste(self, *a, **kw):
        return UnPaste(*a, **kw)

    def post_paste(self, paste, max_age=None):
        if max_age is None:
            max_code = 'week'
        else:
            max_code = self.EXPIRATIONS[self.get_closest_expiration(max_age)]

        d = self.browser.post_image(paste.title, paste.contents.decode('base64'), max_code)
        paste.id = d['id']
        return paste

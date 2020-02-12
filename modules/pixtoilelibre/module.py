# -*- coding: utf-8 -*-

# Copyright(C) 2014      Vincent A
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
import re

from weboob.tools.backend import Module
from weboob.capabilities.paste import CapPaste, BasePaste
from weboob.tools.capabilities.paste import image_mime, bin_to_b64

from .browser import PixtoilelibreBrowser


__all__ = ['PixtoilelibreModule']


class PixPaste(BasePaste):
    @classmethod
    def id2url(cls, id):
        return 'http://pix.toile-libre.org/?img=%s' % id


class PixtoilelibreModule(Module, CapPaste):
    NAME = 'pixtoilelibre'
    DESCRIPTION = u'toile-libre image hosting website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    BROWSER = PixtoilelibreBrowser

    def can_post(self, contents, title=None, public=None, max_age=None):
        if re.search(r'[^a-zA-Z0-9=+/\s]', contents):
            return 0
        elif max_age:
            return 0 # expiration is not possible
        else:
            mime = image_mime(contents, ('gif', 'jpeg', 'png'))
            return 20 * int(mime is not None)

    def get_paste(self, id):
        m = self.browser.img.match(id)
        if m:
            id = m.group('id')
        paste = PixPaste(id)
        contents = self.browser.get_contents(id)
        if contents:
            paste.contents = bin_to_b64(contents)
            return paste

    def new_paste(self, *a, **kw):
        return PixPaste(*a, **kw)

    def post_paste(self, paste, max_age=None):
        d = self.browser.post_image(paste.title or '-', b64decode(paste.contents), private=(not paste.public), description=paste.title)
        paste.id = d['id']
        return paste

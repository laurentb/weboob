# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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

from weboob.tools.backend import Module
from weboob.capabilities.paste import CapPaste, BasePaste
from weboob.tools.capabilities.paste import image_mime
from weboob.capabilities.base import StringField

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


class ImgurModule(Module, CapPaste):
    NAME = 'imgur'
    DESCRIPTION = u'imgur image upload service'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.1'

    BROWSER = ImgurBrowser

    IMGURL = re.compile(r'https?://(?:[a-z]+\.)?imgur.com/([a-zA-Z0-9]+)(?:\.[a-z]+)?$')
    ID = re.compile(r'[0-9a-zA-Z]+$')

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
        paste.contents = bin.encode('base64')
        return paste

    def post_paste(self, paste, max_age=None):
        res = self.browser.post_image(b64=paste.contents, title=paste.title)
        paste.id = res['id']
        paste.delete_url = res['delete_url']
        return paste

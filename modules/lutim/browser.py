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

from base64 import b64decode, b64encode
import math
from io import BytesIO

from weboob.browser import PagesBrowser, URL
from weboob.tools.compat import urljoin

from .pages import ImagePage, UploadPage


class LutimBrowser(PagesBrowser):
    BASEURL = 'https://lut.im'
    VERIFY = False # XXX SNI is not supported

    image_page = URL('/(?P<id>.+)', ImagePage)
    upload_page = URL('/', UploadPage)

    def __init__(self, base_url, *args, **kw):
        PagesBrowser.__init__(self, *args, **kw)
        self.base_url = self.BASEURL = base_url

    def fetch(self, paste):
        self.location(paste.id)
        assert self.image_page.is_here()
        paste.contents = b64encode(self.page.contents).decode('ascii')
        paste.title = self.page.filename

    def post(self, paste, max_age=0):
        bin = b64decode(paste.contents)
        name = paste.title or 'file' # filename is mandatory
        filefield = {'file': (name, BytesIO(bin))}
        params = {'format': 'json'}
        if max_age:
            params['delete-day'] = int(math.ceil(max_age / 86400.))
        self.location('/', data=params, files=filefield)
        assert self.upload_page.is_here()
        info = self.page.fetch_info()
        paste.id = urljoin(self.base_url, info['short'])

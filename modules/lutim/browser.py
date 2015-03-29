# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
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


import math
from urlparse import urljoin
from StringIO import StringIO
from weboob.browser import PagesBrowser, URL

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
        paste.contents = unicode(self.page.contents.encode('base64'))
        paste.title = self.page.filename

    def post(self, paste, max_age=0):
        bin = paste.contents.decode('base64')
        name = paste.title or 'file' # filename is mandatory
        filefield = {'file': (name, StringIO(bin))}
        params = {'format': 'json'}
        if max_age:
            params['delete-day'] = math.ceil(max_age / 86400.)
        self.location('/', data=params, files=filefield)
        assert self.upload_page.is_here()
        info = self.page.fetch_info()
        paste.id = urljoin(self.base_url, info['short'])

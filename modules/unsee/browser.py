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


from weboob.deprecated.browser import Browser
import os
from uuid import uuid4
from urllib2 import Request
from weboob.tools.compat import urljoin
from weboob.tools.json import json
from weboob.deprecated.browser.parsers.lxmlparser import LxmlHtmlParser


__all__ = ['UnseeBrowser']


def to_bytes(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s


class FileField(object):
    def __init__(self, filename, contents=None, headers=None):
        self.filename = to_bytes(os.path.basename(filename))
        self.headers = headers or {}
        if contents is not None:
            self.contents = contents
        else:
            self.contents = open(filename).read()


class UnseeBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'unsee.cc'
    ENCODING = 'utf-8'

    def _make_boundary(self):
        return '==%s==' % uuid4()

    def _make_multipart(self, pairs, boundary):
        s = []
        for k, v in pairs:
            s.append('--%s' % boundary)
            if isinstance(v, FileField):
                s.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (k, v.filename))
                for hk, hv in v.headers.items():
                    s.append('%s: %s' % (hk, hv))
                v = v.contents
            else:
                s.append('Content-Disposition: form-data; name="%s"' % k)
            s.append('')
            s.append(to_bytes(v))
        s.append('--%s--' % boundary)
        s.append('')
        return '\r\n'.join(s)

    def _multipart(self, url, fields):
        b = self._make_boundary()
        data = self._make_multipart(fields, b)
        headers = {'Content-type': 'multipart/form-data; boundary=%s' % b, 'Content-length': len(data)}
        return Request(url, data=self._make_multipart(fields, b), headers=headers)

    def post_image(self, name, contents, time):
        # time='first' for one-shot view

        params = [('time', time), ('image[]', FileField(name or '-', contents))]
        request = self._multipart('https://unsee.cc/upload/', params)

        d = json.loads(self.readurl(request))
        return {'id': d['hash']}

    def get_image(self, id):
        doc = self.get_document(self.openurl('https://unsee.cc/%s/' % id))
        images = LxmlHtmlParser.select(doc, '//img/@src[starts-with(., "/image/")]', method='xpath')
        url = urljoin('https://unsee.cc', images[0])
        return self.readurl(url)

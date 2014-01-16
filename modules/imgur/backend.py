# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.backend import BaseBackend
from weboob.capabilities.paste import ICapPaste, BasePaste
from weboob.tools.capabilities.paste import image_mime
from weboob.capabilities.base import StringField
from weboob.tools.browser import StandardBrowser
from urllib import urlencode
import re


__all__ = ['ImgurBackend']


class ImgPaste(BasePaste):
    delete_url = StringField('URL to delete the image')

    @classmethod
    def id2url(cls, id):
        return 'http://imgur.com/%s' % id

    @property
    def raw_url(self):
        # TODO get the right extension
        return 'http://i.imgur.com/%s.png' % self.id


class ImgurBackend(BaseBackend, ICapPaste):
    NAME = 'imgur'
    DESCRIPTION = u'imgur image upload service'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '0.i'

    CLIENT_ID = '87a8e692cb09382'

    #BROWSER = ImgurBrowser
    BROWSER = StandardBrowser

    def create_default_browser(self):
        return self.create_browser(parser='json')

    def do_get(self, url):
        return self.do_request(url, None)

    def do_post(self, url, data):
        return self.do_request(url, data)

    def do_request(self, url, data):
        headers = {'Authorization': 'Client-ID %s' % self.CLIENT_ID}
        request = self.browser.request_class(url, data, headers)
        return self.browser.get_document(self.browser.openurl(request))

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

    def post_paste(self, paste, max_age=None):
        params = dict(image=paste.contents, title=paste.title, type='base64')
        json = self.do_post('https://api.imgur.com/3/image', urlencode(params))
        if json['success']:
            paste.id = json['data']['id']
            paste.delete_url = 'https://api.imgur.com/3/image/%s' % json['data']['deletehash']

    def get_paste(self, id):
        paste = ImgPaste(id)
        paste.contents = self.browser.readurl(paste.raw_url).encode('base64')
        return paste

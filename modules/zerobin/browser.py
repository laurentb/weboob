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

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.date import DateField
from weboob.capabilities.paste import BasePaste

from .pages import ReadPageZero, ReadPage0, WritePageZero, WritePage0


class ZeroPaste(BasePaste):
    expire = DateField('Expire date')

    @property
    def page_url(self):
        return self.url


class ZerobinBrowser(PagesBrowser):
    BASEURL = 'https://zerobin.net/'

    read_page_zero = URL(r'https?://.*/\?(?P<id>[\w+-]+)$', ReadPageZero)
    read_page_0 = URL(r'https?://.*/paste/(?P<id>[\w+-]+)$', ReadPage0)
    write_page_zero = URL('.*', WritePageZero)
    write_page_0 = URL('.*', WritePage0)

    def __init__(self, baseurl, opendiscussion, *args, **kwargs):
        super(ZerobinBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = baseurl
        self.opendiscussion = opendiscussion

    def get_paste(self, url):
        server_url, key = url.split('#')
        self.location(server_url)
        if not (self.read_page_zero.is_here() or self.read_page_0.is_here()):
            return None

        ret = ZeroPaste(url)
        ret.url = url
        ret.contents = self.page.decode_paste(key)
        ret.public = False
        ret.title = self.page.params['id']
        if hasattr(self.page, 'get_expire'):
            ret.expire = self.page.get_expire()
            # TODO impl in ReadPage0
        return ret

    def can_post(self, contents, max_age):
        self.location(self.BASEURL)

        if max_age not in self.page.AGES:
            return 0

        # TODO reject binary files on zerobin?
        return 1

    def post_paste(self, p, max_age):
        self.location(self.BASEURL)
        p.url = self.page.post(p.contents, max_age)
        p.id = p.url

        server_url, _ = p.url.split('#')
        m = self.read_page_0.match(server_url) or self.read_page_zero.match(server_url)
        p.title = m.group('id')

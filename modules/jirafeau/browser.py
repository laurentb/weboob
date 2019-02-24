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

from __future__ import division
from __future__ import unicode_literals

import math
import re

from weboob.browser import PagesBrowser, URL

from .pages import PageUpload, PageFile

class JirafeauBrowser(PagesBrowser):
    BASEURL = 'https://jirafeau.net/'

    dl_page = URL(r'f.php\?h=(?P<id>[^&%]+)&d=1$')
    file_page = URL(r'f.php\?h=(?P<id>[^&%]+)$', PageFile)
    del_page = URL(r'f.php\?h=(?P<id>[^&%]+)&d=(?P<edit_key>[^&%]{2,})$')
    upload_page = URL('$', PageUpload)

    max_size = 0

    age_keyword = {
        60: 'minute',
        3600: 'hour',
        86400: 'day',
        7 * 86400: 'week',
        28 * 86400: 'month',
    }

    def __init__(self, base_url, *args, **kwargs):
        self.BASEURL = base_url
        super(JirafeauBrowser, self).__init__(*args, **kwargs)

    def recognize(self, url):
        match = self.dl_page.match(url) or self.file_page.match(url) or self.del_page.match(url)
        if match:
            _id = match.group('id')
            return {
                'id': _id,
                'url': self.file_page.build(id=_id)
            }
        elif re.match('[a-zA-Z0-9_-]+$', url):
            return {
                'id': url,
                'url': self.file_page.build(id=url),
            }

    def exists(self, _id):
        self.file_page.stay_or_go(id=_id)
        assert self.file_page.is_here()
        return self.page.has_error()

    def download(self, _id):
        if not _id.startswith('http'):
            _id = self.dl_page.build(id=_id)
        return self.open(_id).content

    def check_error(self, response):
        if response.text.startswith('Error'):
            raise Exception('Site returned an error: %s' % response.text)

    def post(self, contents, title=None, max_age=None, one_time=False):
        max_size, async_size = self.get_max_sizes()

        assert not max_size or len(contents) <= max_size
        if len(contents) < async_size:
            return self._basic_post(contents, title, max_age, one_time)
        else:
            return self._chunked_post(contents, title, max_age, one_time, async_size // 2)

    def _basic_post(self, contents, title=None, max_age=None, one_time=False):
        params = {}
        if one_time:
            params['one_time_download'] = 1
        params['time'] = self.age_keyword[max_age]

        files = {
            'file': (title or '', contents)
        }

        response = self.open('script.php', data=params, files=files)
        self.check_error(response)

        _id, edit_key = response.text.split()
        return {
            'id': _id,
            'edit_key': edit_key,
            'page_url': self.file_page.build(id=_id),
            'download_url': self.dl_page.build(id=_id),
            'delete_url': self.del_page.build(id=_id, edit_key=edit_key),
        }

    def _chunked_post(self, contents, title=None, max_age=None, one_time=False, chunk_size=None):
        title = title or ''

        params = {}
        if one_time:
            params['one_time_download'] = 1
        params['time'] = self.age_keyword[max_age]
        params['filename'] = title

        response = self.open('script.php?init_async', data=params)
        self.check_error(response)
        _id, edit_key = response.text.split('\n')

        chunk_size = chunk_size or (16 << 20)
        chunks = int(math.ceil(len(contents) / chunk_size))
        i = 1
        while contents:
            data, contents = contents[:chunk_size], contents[chunk_size:]
            params = {
                'ref': _id,
                'code': edit_key,
            }
            files = {
                'data': (title, data),
            }

            self.logger.debug('uploading part %d/%d', i, chunks)
            response = self.open('script.php?push_async', data=params, files=files)
            self.check_error(response)
            edit_key = response.text.split('\n')[0]
            i += 1

        params = {
            'ref': _id,
            'code': edit_key,
        }
        response = self.open('script.php?end_async', data=params)
        self.check_error(response)
        _id, edit_key, password = response.text.split('\n')

        return {
            'id': _id,
            'edit_key': edit_key,
            'page_url': self.file_page.build(id=_id),
            'download_url': self.dl_page.build(id=_id),
            'delete_url': self.del_page.build(id=_id, edit_key=edit_key),
        }

    def get_max_sizes(self):
        self.upload_page.stay_or_go()
        assert self.upload_page.is_here()
        return self.page.get_max_sizes()

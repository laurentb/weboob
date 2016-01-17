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


from weboob.browser.browsers import APIBrowser


class ImgurBrowser(APIBrowser):
    BASEURL = 'https://api.imgur.com'

    CLIENT_ID = '87a8e692cb09382'

    def open_raw(self, *args, **kwargs):
        return super(ImgurBrowser, self).open(*args, **kwargs)

    def open(self, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = 'Client-ID %s' % self.CLIENT_ID
        return super(ImgurBrowser, self).open(*args, **kwargs)

    def post_image(self, b64, title=''):
        res = {}
        params = {'image': b64, 'title': title or '', 'type': 'base64'}
        json = self.request('https://api.imgur.com/3/image', data=params)
        if json['success']:
            res['id'] = json['data']['id']
            res['delete_url'] = 'https://api.imgur.com/3/image/%s' % json['data']['deletehash']
            return res

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Vincent Paredes
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
from json import loads

from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText


class LoginPage(HTMLPage):
    def login(self, username, password):
        for script in self.doc.xpath('//script'):
            txt = CleanText('.')(script)
            m = re.search('headers: \'(\{.*?\})', txt)
            if m:
                headers = loads(m.group(1))
                break

        data = {}
        data['forcePwd'] = False
        data['login'] = username
        data['mem'] = True
        data['params'] = {}
        data['params']['return_url'] = 'https://www.sosh.fr/'
        data['params']['service'] = 'sosh'
        response = self.browser.location('https://login.orange.fr/front/login', json=data, headers=headers)

        headers['x-auth-id'] = response.headers['x-auth-id']
        headers['x-xsrf-token'] = response.headers['x-xsrf-token']

        data = {}
        data['login'] = username
        data['password'] = password
        data['params'] = {}
        data['params']['return_url'] = 'https://www.sosh.fr/'
        data['params']['service'] = 'sosh'

        self.browser.location('https://login.orange.fr/front/password', json=data, headers=headers)

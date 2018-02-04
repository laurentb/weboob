# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from base64 import b64encode
from collections import OrderedDict
from io import BytesIO

from weboob.capabilities.captcha import UnsolvableCaptcha
from weboob.browser import DomainBrowser
from weboob.tools.compat import parse_qsl


def parse_qs(d):
    return dict(parse_qsl(d))


class DeathbycaptchaBrowser(DomainBrowser):
    BASEURL = 'http://api.dbcapi.me'

    def __init__(self, username, password, *args, **kwargs):
        super(DeathbycaptchaBrowser, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password

    def check_correct(self, reply):
        if reply.get('is_correct', '1') == 0:
            raise UnsolvableCaptcha()

    def create_job(self, data):
        data64 = 'base64:%s' % b64encode(data)
        files = {
            'captchafile': ('captcha.jpg', BytesIO(data64.encode('ascii'))),
        }

        post = OrderedDict([
            ('username', self.username),
            ('password', self.password),
        ])

        r = self.open('/api/captcha', data=post, files=files)
        reply = parse_qs(r.text)
        self.check_correct(reply)

        return reply['captcha']

    def poll(self, id):
        r = self.open('/api/captcha/%s' % id)
        reply = parse_qs(r.text)
        self.check_correct(reply)

        return reply['text'] or None

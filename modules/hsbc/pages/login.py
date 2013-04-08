# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
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
import urllib
from mechanize import FormNotFoundError

from weboob.tools.browser import BasePage, BrokenPageError


__all__ = ['LoginPage']


class LoginPage(BasePage):
    def on_loaded(self):
        try:
            self.browser.select_form(name="form1")
        except FormNotFoundError:
            pass
        else:
            self.browser.submit(nologin=True)

    def login(self, username, secret, password):
        form_world = self.document.xpath('//form[@name="auth04"]')
        url = form_world[0].attrib['action']
        datastr = "TF1;015;;;;;;;;;;;;;;;;;;;;;;Mozilla;Netscape;5.0%20%28X11%29;20100101;undefined;true;Linux%20x86_64;true;Linux%20x86_64;undefined;Mozilla/5.0%20%28X11%3B%20Linux%20x86_64%3B%20rv%3A19.0%29%20Gecko/20100101%20Firefox/19.0%20Iceweasel/19.0.2;en-US;undefined;www.hsbc.fr;undefined;undefined;undefined;undefined;true;true;1365177015380;1;Tue%2007%20Jun%202005%2009%3A33%3A44%20PM%20CEST;1280;1024;;11.2;;;;;123;-60;-120;Fri%2005%20Apr%202013%2005%3A50%3A15%20PM%20CEST;24;1280;1024;0;0;;;;;;Shockwave%20Flash%7CShockwave%20Flash%2011.2%20r202;;;;;;;;;;;;;17;"
        data = {'FMNUserId': username,
                'memorableAnswer': secret,
                'password': '',
                '__data': datastr,
                '__custtype': 'GLOBAL',

               }
        for i, field in enumerate(form_world[0].xpath('.//div[@class="csLabel"]/nobr/input[@type="password"]')):
            if field.attrib['name'].startswith('keyrcc_password_first') and not 'disabled' in field.attrib:
                data[field.attrib['name']] = password[i]
                data['password'] += password[i]

        if url.startswith('/'):
            url = 'https://www.hsbc.fr%s' % url

        self.browser.location(url, urllib.urlencode(data), no_login=True)

    def get_error(self):
        try:
            return self.parser.tocleanstring(self.document.xpath('//font[@color="red"]')[0])
        except IndexError:
            return None

    def get_session(self):
        try:
            frame = self.document.xpath('//frame[@name="FrameWork"]')[0]
        except IndexError:
            raise BrokenPageError('Unable to find session token')

        m = re.search('sessionid=([^& "]+)', frame.attrib['src'])
        if not m:
            raise BrokenPageError('Unable to find session token')
        return m.group(1)

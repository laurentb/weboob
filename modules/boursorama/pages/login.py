# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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
import hashlib
import urllib

from weboob.deprecated.browser import Page, BrowserIncorrectPassword
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard


class VirtKeyboard(MappedVirtKeyboard):
    symbols={'0':'40fdd263e99d7268b49e22e06b73ebf1',
             '1':'0d53ac10dba67d3ec601a086d0881b6f',
             '2':'91b6e36e32ef8650127367a076b03c34',
             '3':'bbda594275b7999fdac947e2499e7884',
             '4':'26cd3d8f2279b5ec2be6d6f2be1e9c78',
             '5':'408ceca0885b6ae720745531587f2766',
             '6':'9008178542bdad8b9cbcd4d8a551f2fa',
             '7':'3ab5c3555f36617d264d4938f487480c',
             '8':'c06676612c15345c3634af51c058e64f',
             '9':'d8323299dd4bd6489480b1e402fa5bcc'
            }

    color=(0,0,0)

    def check_color(self, color):
        r, g, b = color
        return r > 240 and g > 240 and b > 240

    def __init__(self, page):
        img = page.document.find("//img[@usemap='#login-pad_map']")
        img_file = page.browser.openurl(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, img_file, page.document, img, self.color, convert='RGB')

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def get_symbol_code(self,md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self,md5sum)
        return re.search("'(\w{3}\|)'", code).group(1)

    def get_string_code(self,string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

    def checksum(self, coords):
        x1, y1, x2, y2 = coords
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                # strip pixels on borders
                if self.check_color(self.pixar[x, y]) and x > x1+2 and y > y1+2 and x < x2-2 and y < y2-2:
                    s += "."
                else:
                    s += " "
        return hashlib.md5(s).hexdigest()


class LoginPage(Page):
    def on_loaded(self):
        pass
#        for td in self.document.getroot().cssselect('td.LibelleErreur'):
#            if td.text is None:
#                continue
#            msg = td.text.strip()
#            if 'indisponible' in msg:
#                raise BrowserUnavailable(msg)

    def login(self, login, password):
        vk = VirtKeyboard(self)

        form = self.document.xpath('//form[@name="identification"]')[0]
        args = {'login':                    login,
                'password':                 vk.get_string_code(password),
                'password_fake':            '*' * len(password),
                'org':                      '',
                'redirect':                 '',
               }

        self.browser.location(form.attrib['action'], urllib.urlencode(args), no_login=True)


class UpdateInfoPage(Page):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Please update your login credentials')

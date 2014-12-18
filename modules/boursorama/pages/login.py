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
    symbols={'0':'cb9af3f561915702fc7f8ebaed8d5024',
             '1':'6154d49517dce772aedb581db6587f12',
             '2':'e8b1f8242ff536a807a91e521921a6ea',
             '3':'55ae6e699ff2a09c97e58dbad410d2d5',
             '4':'b23b8dfe923349f2b082b0a30965dd49',
             '5':'b0f2d0f28662c32ad82233313a4074f6',
             '6':'ffb10411571a767e9f6e7c8229a5bdac',
             '7':'ba8650fd57b2648ca91679d574150a9b',
             '8':'cbf9b18012499c023f1e78dcc3611cce',
             '9':'c70a99af7bc6a03f28b1217e58363ecf'
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

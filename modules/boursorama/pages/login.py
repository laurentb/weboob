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
import tempfile

from weboob.tools.browser import BasePage, BrowserIncorrectPassword
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard


__all__ = ['LoginPage']


class VirtKeyboard(MappedVirtKeyboard):
    symbols={'0':'e1bcad576e43320e0f3b0c7c14895433',
             '1':'dee70a13b9002b820059bb976a9be880',
             '2':'e4969fc2cc6f02d1e9fd4bbc6b5d4f6c',
             '3':'bb83b43088b40a7cf1d01627ba908e42',
             '4':'0711fee716ecbf7c42d9c8836ad990bb',
             '5':'7dd995622fac18df1c492934516380fd',
             '6':'97e22311e482964823087ead7e7ba1cc',
             '7':'6326d9d72be0c3e9b52c691ff3ca4ccd',
             '8':'b67a2a4ac01d71b5184d4fafb40be9a2',
             '9':'e4389eea90bea5dc5652ef773d7dc10c'
            }

    color=(0,0,0)

    def check_color(self, (r, g, b)):
        return r > 240 and g > 240 and b > 240

    def __init__(self, page):
        img = page.document.find("//img[@usemap='#pass_map']")
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

    def checksum(self, (x1, y1, x2, y2)):
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                # strip pixels on borders
                if self.check_color(self.pixar[x, y]) and x > x1+2 and y > y1+2 and x < x2-2 and y < y2-2:
                    s += "."
                else:
                    s += " "
        return hashlib.md5(s).hexdigest()

class LoginPage(BasePage):
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

class UpdateInfoPage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Please update your user informations')

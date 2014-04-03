# -*- coding: utf-8 -*-

# Copyright(C) 2012  Florent Fourcot
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


import time

try:
    from PIL import Image
except ImportError:
    raise ImportError('Please install python-imaging')

from weboob.tools.browser import BasePage

__all__ = ['LoginPage']


class FreeKeyboard(object):
    DEBUG = False
    symbols = {'0': '001111111111110011111111111111111111111111111110000000000011110000000000011111111111111111011111111111111001111111111110',
               '1': '001110000000000001110000000000001110000000000011111111111111111111111111111111111111111111000000000000000000000000000000',
               '2': '011110000001111011110000111111111000001111111110000011110011110000111100011111111111000011011111110000011001111000000011',
               '3': '011100000011110111100000011111111000110000111110000110000011110001110000011111111111111111011111111111110001110001111100',
               '4': '000000011111000000001111111000000111110011000011110000011000111111111111111111111111111111111111111111111000000000011000',
               '5': '111111110011110111111110011111111001110000111111001100000011111001100000011111001111111111111001111111111010000111111110',
               '6': '001111111111110011111111111111111111111111111110001100000011110001100000011111001111111111111101111111111011100111111110',
               '7': '111000000000000111000000000000111000000011111111000011111111111011111111111111111111000000111111000000000111100000000000',
               '8': '001110001111110011111111111111111111111111111110000110000011110000110000011111111111111111011111111111111001111001111110',
               '9': '001111111000110011111111100111111111111100111110000001100011110000001100011111111111111111011111111111111001111111111110'
              }

    def __init__(self, basepage):
        self.basepage = basepage
        self.fingerprints = []
        for htmlimg in basepage.document.xpath('//img[@class="ident_chiffre_img pointer"]'):
            url = htmlimg.attrib.get("src")
            fichier = basepage.browser.openurl(url)
            image = Image.open(fichier)
            matrix = image.load()
            s = ""
            # The digit is only displayed in the center of image
            for x in range(15, 23):
                for y in range(12, 27):
                    (r, g, b) = matrix[x, y]
                    # If the pixel is "red" enough
                    if g + b < 450:
                        s += "1"
                    else:
                        s += "0"

            self.fingerprints.append(s)
            if self.DEBUG:
                image.save('/tmp/' + s + '.png')

    def get_symbol_code(self, digit):
        fingerprint = self.symbols[digit]
        i = 0
        for string in self.fingerprints:
            if string == fingerprint:
                return i
            i += 1
        # Image contains some noise, and the match is not always perfect
        # (this is why we can't use md5 hashs)
        # But if we can't find the perfect one, we can take the best one
        i = 0
        best = 0
        result = None
        for string in self.fingerprints:
            j = 0
            match = 0
            for bit in string:
                if bit == fingerprint[j]:
                    match += 1
                j += 1
            if match > best:
                best = match
                result = i
            i += 1
        self.basepage.browser.logger.debug(self.fingerprints[result] + " match " + digit)
        return result

        # TODO : exception

    def get_string_code(self, string):
        code = ''
        for c in string:
            codesymbol = self.get_symbol_code(c)
            code += str(codesymbol)
        return code

    def get_small(self, string):
        for c in string:
            time.sleep(0.5)
            url = 'https://mobile.free.fr/moncompte/chiffre.php?pos=' + c + '&small=1'
            self.basepage.browser.openurl(url)


class LoginPage(BasePage):
    def on_loaded(self):
        pass

    def login(self, login, password):
        vk = FreeKeyboard(self)

        # Fucking form without name...
        self.browser.select_form(nr=0)
        self.browser.set_all_readonly(False)
        code = vk.get_string_code(login)
        self.browser['login_abo'] = code.encode('utf-8')
        vk.get_small(code)
        self.browser['pwd_abo'] = password.encode('utf-8')
        self.browser.submit(nologin=True)

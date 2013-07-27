# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
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


from weboob.tools.mech import ClientForm
from logging import error

from weboob.tools.browser import BasePage, BrowserIncorrectPassword
from weboob.tools.captcha.virtkeyboard import VirtKeyboard, VirtKeyboardError


__all__ = ['LoginPage', 'INGVirtKeyboard', 'StopPage']


class INGVirtKeyboard(VirtKeyboard):
    symbols = {'0': '327208d491507341908cf6920f26b586',
               '1': '615ff37b15645da106cebc4605b399de',
               '2': 'fb04e648c93620f8b187981f9742b57e',
               '3': 'b786d471a70de83657d57bdedb6a2f38',
               '4': '41b5501219e8d8f6d3b0baef3352ce88',
               '5': 'c72b372fb035160f2ff8dae59cd7e174',
               '6': '392fa79e9a1749f5c8c0170f6a8ec68b',
               '7': 'fb495b5cf7f46201af0b4977899b56d4',
               '8': 'e8fea1e1aa86f8fca7f771db9a1dca4d',
               '9': '82e63914f2e52ec04c11cfc6fecf7e08'
              }
    color = 64

    def __init__(self, basepage):
        divkeyboard = basepage.document.find("//div[@id='clavierdisplayLogin']")
        if divkeyboard is None:
            divkeyboard = basepage.document.find("//div[@id='claviertransfer']")
        try:
            img = divkeyboard.xpath("img")[1]
        except:
            raise BrowserIncorrectPassword()
        url = img.attrib.get("src")
        coords = {}
        coords["11"] = (5, 5, 33, 33)
        coords["21"] = (45, 5, 73, 33)
        coords["31"] = (85, 5, 113, 33)
        coords["41"] = (125, 5, 153, 33)
        coords["51"] = (165, 5, 193, 33)
        coords["12"] = (5, 45, 33, 73)
        coords["22"] = (45, 45, 73, 73)
        coords["32"] = (85, 45, 113, 73)
        coords["42"] = (125, 45, 153, 73)
        coords["52"] = (165, 45, 193, 73)

        VirtKeyboard.__init__(self, basepage.browser.openurl(url), coords, self.color)

        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_string_code(self, string):
        code = ''
        first = True
        for c in string:
            if not first:
                code += ","
            else:
                first = False
            codesymbol = self.get_symbol_code(self.symbols[c])
            x = (self.coords[codesymbol][0] + self.coords[codesymbol][2]) / 2
            y = (self.coords[codesymbol][1] + self.coords[codesymbol][3]) / 2
            code += str(x)
            code += ","
            code += str(y)
        return code


class LoginPage(BasePage):
    def on_loaded(self):
        pass

    def prelogin(self, login, birthday):
        # First step : login and birthday
        self.browser.select_form('zone1Form')
        self.browser.set_all_readonly(False)
        self.browser['zone1Form:numClient'] = str(login)
        self.browser['zone1Form:dateDay'] = str(birthday[0:2])
        self.browser['zone1Form:dateMonth'] = str(birthday[2:4])
        self.browser['zone1Form:dateYear'] = str(birthday[4:9])
        self.browser['zone1Form:idRememberMyCifCheck'] = False
        self.browser.submit(nologin=True)

    def error(self):
        err = self.document.find('//span[@class="error"]')
        return err is not None

    def login(self, password):
        # 2) And now, the virtual Keyboard
        try:
            vk = INGVirtKeyboard(self)
        except VirtKeyboardError as err:
            error("Error: %s" % err)
            return False
        realpasswd = ""
        span = self.document.find('//span[@id="digitpaddisplayLogin"]')
        i = 0
        for font in span.getiterator('font'):
            if font.attrib.get('class') == "vide":
                realpasswd += password[i]
            i += 1
        self.browser.logger.debug('We are looking for : ' + realpasswd)
        self.browser.select_form('mrc')
        self.browser.set_all_readonly(False)
        self.browser.logger.debug("Coordonates: " + vk.get_string_code(realpasswd))
        self.browser.controls.append(ClientForm.TextControl('text', 'mrc:mrg', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'AJAXREQUEST', {'value': ''}))
        self.browser['AJAXREQUEST'] = '_viewRoot'
        self.browser['mrc:mrldisplayLogin'] = vk.get_string_code(realpasswd)
        self.browser['mrc:mrg'] = 'mrc:mrg'
        self.browser.submit(nologin=True)


class StopPage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Please login on website to fill the form and retry')

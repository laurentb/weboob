# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Pierre Mazière
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
import re
import urllib

from weboob.deprecated.browser import Page, BrowserUnavailable
from weboob.tools.captcha.virtkeyboard import VirtKeyboard, VirtKeyboardError


class BNPVirtKeyboard(VirtKeyboard):
    symbols={'0': '9cc4789a2cb223e8f2d5e676e90264b5',
             '1': 'e10b58fc085f9683052d5a63c96fc912',
             '2': '04ec647e7b3414bcc069f0c54eb55a4c',
             '3': 'fde84fd9bac725db8463554448f1e469',
             '4': '2359eea8671bf112b58264bec0294f71',
             '5': '82b55b63480114f04fad8c5c4fa5673a',
             '6': 'e074864faeaeabb3be3d118192cd8879',
             '7': 'af5740e4ca71fadc6f4ae1412d864a1c',
             '8': 'cab759c574038ad89a0e35cc76ab7214',
             '9': '828cf0faf86ac78e7f43208907620527'
            }

    url="/NSImgGrille?timestamp=%d"

    color=27

    def __init__(self, page):
        coords = {}

        size = 136
        x, y, width, height = (0, 0, size/5, size/5)
        for a in page.document.xpath('//div[@id="secret-nbr-keyboard"]/a'):
            code = a.attrib['ondblclick']
            coords[code] = (x+1, y+1, x+height-2, y+height-2)
            if (x + width + 1) >= size:
                y += height
                x = 0
            else:
                x += width

        VirtKeyboard.__init__(self, page.browser.openurl(self.url % time.time()), coords, self.color)

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code = VirtKeyboard.get_symbol_code(self, md5sum)
        return re.sub(u'[^\d]', '', code)

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(Page):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def login(self, login, password):
        try:
            vk=BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s"%err)
            return False

        # Mechanize does not recognize the form..
        form = self.document.xpath('//form[@name="logincanalnet"]')[0]
        url = form.attrib['action']
        params = {}
        for ctrl in form.findall('input'):
            params[ctrl.attrib['name']] = ctrl.attrib['value']

        params['ch1'] = login.encode('iso-8859-1')
        params['ch5'] = vk.get_string_code(password)

        self.browser.location(url, urllib.urlencode(params))


class ConfirmPage(Page):
    def get_error(self):
        for td in self.document.xpath('//td[@class="hdvon1"]'):
            if td.text:
                return td.text.strip()
        return None

    def get_relocate_url(self):
        script = self.document.xpath('//script')[0]
        m = re.match('document.location.replace\("(.*)"\)', script.text[script.text.find('document.location.replace'):])
        if m:
            return m.group(1)


class InfoMessagePage(Page):
    def on_loaded(self):
        pass


class ChangePasswordPage(Page):
    def change_password(self, current, new):
        try:
            vk=BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s"%err)
            return False

        from mechanize import Cookie
        c = Cookie(0, 'wbo_segment_369721', 'AA%7CAB%7C%7C%7C',
                      None, False,
                      '.secure.bnpparibas.net', True, True,
                      '/', False,
                      False,
                      None,
                      False,
                      None,
                      None,
                      {})
        cookiejar = self.browser._ua_handlers["_cookies"].cookiejar

        cookiejar.set_cookie(c)

        code_current=vk.get_string_code(current)
        code_new=vk.get_string_code(new)

        data = (('ch1', code_current),
                ('ch2', code_new),
                ('radiobutton3', 'radiobutton'),
                ('ch3', code_new),
                ('x', 23),
                ('y', 13),
               )

        headers = {'Referer': self.url}
        #headers = {'Referer': "https://www.secure.bnpparibas.net/SAF_CHM?Action=SAF_CHM&Origine=SAF_CHM&stp=%s" % (int(datetime.now().strftime('%Y%m%d%H%M%S')))}
        #import time
        #time.sleep(10)
        request = self.browser.request_class('https://www.secure.bnpparibas.net/SAF_CHM_VALID', urllib.urlencode(data), headers)
        self.browser.location(request)

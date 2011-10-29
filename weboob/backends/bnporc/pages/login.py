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


from weboob.tools.mech import ClientForm
import urllib
from logging import error

from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.virtkeyboard import VirtKeyboard,VirtKeyboardError
import tempfile

__all__ = ['LoginPage', 'ConfirmPage', 'ChangePasswordPage']


class LoginPage(BasePage):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def login(self, login, password):
        symbols={'0':'9cc4789a2cb223e8f2d5e676e90264b5',
                 '1':'e10b58fc085f9683052d5a63c96fc912',
                 '2':'04ec647e7b3414bcc069f0c54eb55a4c',
                 '3':'fde84fd9bac725db8463554448f1e469',
                 '4':'2359eea8671bf112b58264bec0294f71',
                 '5':'82b55b63480114f04fad8c5c4fa5673a',
                 '6':'e074864faeaeabb3be3d118192cd8879',
                 '7':'753468d88d4810206a6f0ab9c6ef1b16',
                 '8':'9cc4789a2cb223e8f2d5e676e90264b5',
                 '9':'828cf0faf86ac78e7f43208907620527'
                }

        map=self.document.find("//map[@name='MapGril']")

        coords={}
        for area in map.getiterator("area"):
            code=area.attrib.get("onclick")[-4:-2]
            area_coords=[]
            for coord in area.attrib.get("coords").split(","):
                area_coords.append(int(coord))
            coords[code]=tuple(area_coords)

        try:
            vk=VirtKeyboard(self.browser.openurl("/NSImgGrille"),coords,27)
        except VirtKeyboardError,err:
            error("Error: %s" % err)
            return False

        for s in symbols.keys():
            try:
                vk.get_symbol_code(symbols[s])
            except VirtKeyboardError:
                if self.browser.responses_dirname is None:
                    self.browser.responses_dirname = \
                            tempfile.mkdtemp(prefix='weboob_session_')
                vk.generate_MD5(self.browser.responses_dirname)
                error("Error: Symbol '%s' not found; all symbol hashes are available in %s" \
                      % (s,self.browser.responses_dirname))
                return False

        self.browser.select_form('logincanalnet')
        # HACK because of fucking malformed HTML, the field isn't recognized by mechanize.
        self.browser.controls.append(ClientForm.TextControl('text', 'ch1', {'value': ''}))
        self.browser.set_all_readonly(False)

        self.browser['ch1'] = login
        passwd=''
        for c in password:
            passwd+=vk.get_symbol_code(symbols[c])
        self.browser['ch5'] = passwd
        self.browser.submit()


class ConfirmPage(BasePage):
    pass


class ChangePasswordPage(BasePage):
    def change_password(self, current, new):
        symbols={'0':'9cc4789a2cb223e8f2d5e676e90264b5',
                 '1':'e10b58fc085f9683052d5a63c96fc912',
                 '2':'04ec647e7b3414bcc069f0c54eb55a4c',
                 '3':'fde84fd9bac725db8463554448f1e469',
                 '4':'2359eea8671bf112b58264bec0294f71',
                 '5':'82b55b63480114f04fad8c5c4fa5673a',
                 '6':'e074864faeaeabb3be3d118192cd8879',
                 '7':'753468d88d4810206a6f0ab9c6ef1b16',
                 '8':'9cc4789a2cb223e8f2d5e676e90264b5',
                 '9':'828cf0faf86ac78e7f43208907620527'
                }

        map=self.document.find("//map[@name='MapGril']")

        coords={}
        for area in map.getiterator("area"):
            code=area.attrib.get("onclick")[-4:-2]
            area_coords=[]
            for coord in area.attrib.get("coords").split(","):
                area_coords.append(int(coord))
            coords[code]=tuple(area_coords)

        try:
            vk=VirtKeyboard(self.browser.openurl("/NSImgGrille"),coords,27)
        except VirtKeyboardError,err:
            error("Error: %s" % err)
            return False

        for s in symbols.keys():
            try:
                vk.get_symbol_code(symbols[s])
            except VirtKeyboardError:
                if self.browser.responses_dirname is None:
                    self.browser.responses_dirname = \
                            tempfile.mkdtemp(prefix='weboob_session_')
                vk.generate_MD5(self.browser.responses_dirname)
                error("Error: Symbol '%s' not found; all symbol hashes are available in %s" \
                      % (s,self.browser.responses_dirname))
                return False

        code_current=''
        for c in current:
            code_current+=vk.get_symbol_code(symbols[c])

        code_new=''
        for c in new:
            code_new+=vk.get_symbol_code(symbols[c])

        data = {'ch1': code_current,
                'ch2': code_new,
                'ch3': code_new
               }

        self.browser.location('/SAF_CHM_VALID', urllib.urlencode(data))

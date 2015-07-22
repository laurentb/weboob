# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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

from StringIO import StringIO
import hashlib
from decimal import Decimal

from weboob.capabilities.bank import Account
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.json import json


class BNPVirtKeyboard(MappedVirtKeyboard):
    symbols = {'0': 'ff069462836e30a39c911034048f5bb3',
               '1': '7969f04e4e82eaefa2ce7a9a23c26178',
               '2': '1e6020f97ca1c3ce3da4f39ded15d67d',
               '3': 'f84284b40aea93c24814e23e14e76cc8',
               '4': '88bab262d4b344c0ef8f06ddd01adbcf',
               '5': '0a270764fc5d8334bcb55053432b26cb',
               '6': 'e6a4444a6c752cd3e655f2883e530080',
               '7': '933d4ca5df6b2b3df2dea00a21a3fed6',
               '8': ['f28b918777d21a5fde2bffb9899e2138', 'a97e6e27159084d50f8ef00548b70252'],
               '9': 'be751b77af0d998ab4c2cfd38455b2a6',
               }

    color=(0,0,0)

    def __init__(self, basepage):
        img = basepage.doc.xpath('//img[@id="gridpass_img"]')[0]
        imgdata = basepage.browser.open(img.attrib['src']).content
        MappedVirtKeyboard.__init__(self, StringIO(imgdata), basepage.doc, img, self.color, convert='RGB')
        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        code = code.split("'")[3]
        assert code.isdigit()
        return code

    def check_color(self, pixel):
        for p in pixel:
            if p >= 200:
                return False
        return True

    def checksum(self, coords):
        """Copy of parent checksum(), but cropping (removes empty lines)"""
        x1, y1, x2, y2 = coords
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                if self.check_color(self.pixar[x, y]):
                    s += " "
                else:
                    s += "O"
            s += "\n"
        s = '\n'.join([l for l in s.splitlines() if l.strip()])
        return hashlib.md5(s).hexdigest()


class LoginPage(HTMLPage):
    def login(self, login, password):
        try:
            vk = BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s" % err)
            return False

        form = self.get_form(name='loginPwdForm')
        form['txtAuthentMode'] = 'PASSWORD'
        form['txtPwdUserId'] = login
        form['gridpass_hidden_input'] = vk.get_string_code(password)
        form.submit()



class AccountsPage(JsonPage, LoggedPage):
    def iter_accounts(self):
        for f in self.path('tableauSoldes.listeGroupes'):
            for g in f:
                for a in g.get('listeComptes'):
                    yield Account.from_dict({
                        'id': a.get('numeroCompte'),
                        'label': '%s %s' % (a.get('libelleType'), a.get('libelleTitulaire')),
                        'currency': a.get('deviseTenue'),
                        'balance': Decimal(a.get('soldeComptable')) / 100,
                        'coming': Decimal(a.get('soldePrevisionnel')) / 100,
                    })

class HistoryPage(JsonPage, LoggedPage):
    pass

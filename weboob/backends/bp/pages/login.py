# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import hashlib

from weboob.tools.browser import BasePage


__all__ = ['LoginPage', 'LoggedPage', 'BadLoginPage', 'AccountDesactivate']


def md5(file):
    f = open(file,'rb')
    md5 = hashlib.md5()
    md5.update(f.read())
    return md5.hexdigest()


class LoginPage(BasePage):
    def on_loaded(self):
        pass

    def login(self, login, pwd):
        LOCAL_HASH = ['a02574d7bf67677d2a86b7bfc5e864fe', 'eb85e1cc45dd6bdb3cab65c002d7ac8a',
                      '596e6fbd54d5b111fe5df8a4948e80a4', '9cdc989a4310554e7f5484d0d27a86ce',
                      '0183943de6c0e331f3b9fc49c704ac6d', '291b9987225193ab1347301b241e2187',
                      '163279f1a46082408613d12394e4042a', 'b0a9c740c4cada01eb691b4acda4daea',
                      '3c4307ee92a1f3b571a3c542eafcb330', 'dbccecfa2206bfdb4ca891476404cc68',
                      ]
        process = lambda i: md5(self.browser.retrieve(('https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb'
            '/loginform?imgid=%d&0.25122230781963073' % i))[0])
        keypad = [process(i) for i in range(10)]
        correspondance = [keypad.index(i) for i in LOCAL_HASH]
        newpassword = ''.join(str(correspondance[int(c)]) for c in pwd)

        self.browser.select_form(name='formAccesCompte')
        self.browser.set_all_readonly(False)
        self.browser['password'] = newpassword
        self.browser['username'] = login
        self.browser.submit()


class LoggedPage(BasePage):
    pass


class BadLoginPage(BasePage):
    pass


class AccountDesactivate(BasePage):
    pass

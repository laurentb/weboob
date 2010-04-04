# -*- coding: utf-8 -*-

"""
Copyright(C) 2009-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from cStringIO import StringIO

from weboob.tools.browser import Browser, BrowserIncorrectPassword
from weboob.tools.parser import StandardParser
from weboob.backends.bnporc import pages

# Parser
class BNParser(StandardParser):
    def parse(self, data, encoding):
        s = data.read()
        s = s.replace('<?Pub Caret>', '')
        data = StringIO(s)
        return StandardParser.parse(self, data, encoding)

# Browser
class BNPorc(Browser):
    DOMAIN = 'www.secure.bnpparibas.net'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {'.*identifiant=DOSSIER_Releves_D_Operation.*': pages.AccountsList,
             '.*identifiant=DSP_HISTOCPT.*':                pages.AccountHistory,
             '.*NS_AVEEC.*':                                pages.AccountComing,
             '.*NS_AVEDP.*':                                pages.AccountPrelevement,
             '.*Action=DSP_VGLOBALE.*':                     pages.LoginPage,
             '.*type=homeconnex.*':                         pages.LoginPage,
             '.*layout=HomeConnexion':                      pages.ConfirmPage,
            }

    is_logging = False

    def __init__(self, *args, **kwargs):
        kwargs['parser'] = BNParser
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/HomeConnexion?type=homeconnex')

    def is_logged(self):
        return not self.is_on_page(pages.LoginPage) or self.is_logging

    def login(self):
        assert isinstance(self.username, (str,unicode))
        assert isinstance(self.password, (str,unicode))
        assert self.password.isdigit()

        if not self.is_on_page(pages.LoginPage):
            self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/HomeConnexion?type=homeconnex')

        self.is_logging = True
        self.page.login(self.username, self.password)
        self.location('/NSFR?Action=DSP_VGLOBALE')

        if self.is_on_page(pages.LoginPage):
            raise BrowserIncorrectPassword()
        self.is_logging = False

    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, (int, long))

        if not self.is_on_page(pages.AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_coming_operations(self, account):
        if not self.is_on_page(pages.AccountComing) or self.page.account.id != account.id:
            self.location('/NS_AVEEC?ch4=%s' % account.link_id)
        return self.page.get_operations()

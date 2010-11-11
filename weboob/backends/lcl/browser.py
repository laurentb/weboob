# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, LoginErrorPage, AccountsPage


__all__ = ['LCLBrowser']


# Browser
class LCLBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'particuliers.secure.lcl.fr'
    ENCODING = 'utf-8'
    USER_AGENT = 'Wget/1.11.4'
    PAGES = {'https://particuliers.secure.lcl.fr/index.html':   LoginPage,
             'https://particuliers.secure.lcl.fr/everest/UWBI/UWBIAccueil\?DEST=IDENTIFICATION': LoginErrorPage,
             'https://particuliers.secure.lcl.fr/outil/UWSP/Synthese/accesSynthese': AccountsPage
            }
    is_logging = False

    def __init__(self, agency, *args, **kwargs):
        self.agency = agency
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page and not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://particuliers.secure.lcl.fr/', no_login=True)

        self.page.login(self.agency, self.username, self.password)

        if not self.is_logged() or self.is_on_page(LoginErrorPage):
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.home()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, (int, long))

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    #def get_coming_operations(self, account):
    #    if not self.is_on_page(AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon, Pierre Mazière
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

from .pages import LoginPage, LoginResultPage, FramePage, AccountsPage, AccountHistoryPage


__all__ = ['LCLBrowser']


# Browser
class LCLBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'particuliers.secure.lcl.fr'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'https://particuliers.secure.lcl.fr/index.html':   LoginPage,
        'https://particuliers.secure.lcl.fr/everest/UWBI/UWBIAccueil\?DEST=IDENTIFICATION': LoginResultPage,
        'https://particuliers.secure.lcl.fr/outil/UWSP/Synthese/accesSynthese': AccountsPage,
        'https://particuliers.secure.lcl.fr/outil/UWB2/Accueil\?DEST=INIT': FramePage,
        'https://particuliers.secure.lcl.fr/outil/UWLM/ListeMouvementsPro/accesListeMouvementsPro.*':  AccountHistoryPage,
        }

    def __init__(self, agency, *args, **kwargs):
        self.agency = agency
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page and not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()
        assert isinstance(self.agency, basestring)
        assert self.agency.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('%s://%s/index.html' % (self.PROTOCOL, self.DOMAIN),\
                          no_login=True)

        if not self.page.login(self.agency, self.username, self.password) or \
           not self.is_logged() or \
           (self.is_on_page(LoginResultPage) and self.page.is_error()) :
            raise BrowserIncorrectPassword()

        self.location('%s://%s/outil/UWSP/Synthese/accesSynthese' \
                      % (self.PROTOCOL, self.DOMAIN))

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.home()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self,account):
        if not self.is_on_page(AccountHistoryPage) :
            self.location('%s://%s%s' % (self.PROTOCOL, self.DOMAIN, account.link_id))
        return self.page.get_operations()

    #def get_coming_operations(self, account):
    #    if not self.is_on_page(AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()

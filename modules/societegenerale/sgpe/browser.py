# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.tools.ordereddict import OrderedDict

from .pages import LoginPage, AccountsPage


__all__ = ['SGProfessionalBrowser', 'SGEnterpriseBrowser']


class SGPEBrowser(BaseBrowser):
    PROTOCOL = 'https'
    ENCODING = None

    def __init__(self, *args, **kwargs):
        self.PAGES = OrderedDict((
            ('%s://%s/Pgn/.+PageID=Compte&.+' % (self.PROTOCOL, self.DOMAIN), AccountsPage),
            ('%s://%s/' % (self.PROTOCOL, self.DOMAIN), LoginPage),
        ))
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        if not self.page or self.is_on_page(LoginPage):
            return False

        error = self.page.get_error()
        if error is None:
            return True

        return False

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN + '/', no_login=True)

            self.page.login(self.username, self.password)

        # force page change
        if not self.is_on_page(AccountsPage):
            self.accounts()
        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def accounts(self):
        self.location('/Pgn/NavigationServlet?MenuID=%s&PageID=Compte&Classeur=1&NumeroPage=1&Origine=Menu' % self.MENUID)

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.accounts()



class SGProfessionalBrowser(SGPEBrowser):
    DOMAIN = 'professionnels.secure.societegenerale.fr'
    LOGIN_FORM = 'auth_reco'
    MENUID = 'SBORELCPT'


class SGEnterpriseBrowser(SGPEBrowser):
    DOMAIN = 'entreprises.secure.societegenerale.fr'
    LOGIN_FORM = 'auth'
    MENUID = 'BANRELCPT'

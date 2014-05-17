# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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


from weboob.tools.browser2 import LoginBrowser, URL, need_login
from weboob.tools.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage


__all__ = ['AlloRestoBrowser']


class AlloRestoBrowser(LoginBrowser):
    BASEURL = 'http://www.alloresto.fr'

    login =     URL('/identification-requise.*',        LoginPage)
    accounts =  URL('/chez-moi/releve-compte-miams',    AccountsPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.accounts.stay_or_go()
        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        return self.accounts.stay_or_go().iter_accounts()

    @need_login
    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list():
            if a.id == id:
                return a

        return None

    @need_login
    def get_history(self, account):
        return self.accounts.stay_or_go().get_transactions(type='consommable')

    @need_login
    def get_coming(self, account):
        return self.accounts.stay_or_go().get_transactions(type='acquisition')

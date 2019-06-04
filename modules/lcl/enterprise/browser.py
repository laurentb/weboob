# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import AccountOwnerType

from .pages import LoginPage, MovementsPage, ProfilePage, PassExpiredPage


class LCLEnterpriseBrowser(LoginBrowser):
    BASEURL = 'https://entreprises.secure.lcl.fr'

    pass_expired = URL('/outil/IQEN/Authentication/forcerChangePassword', PassExpiredPage)
    login = URL('/outil/IQEN/Authentication/indexRedirect',
                '/outil/IQEN/Authentication/(?P<page>.*)', LoginPage)
    movements = URL('/outil/IQMT/mvt.Synthese/syntheseMouvementPerso',
                    '/outil/IQMT/mvt.Synthese', MovementsPage)
    profile = URL('/outil/IQGA/FicheUtilisateur/maFicheUtilisateur', ProfilePage)

    def __init__(self, *args, **kwargs):
        super(LCLEnterpriseBrowser, self).__init__(*args, **kwargs)
        self.accounts = None
        self.owner_type = AccountOwnerType.ORGANIZATION


    def deinit(self):
        if self.page and self.page.logged:
            self.login.go(page="logout")
            self.login.go(page="logoutOk")
            assert self.login.is_here(page="logoutOk") or self.login.is_here(page="sessionExpiree")
        super(LCLEnterpriseBrowser, self).deinit()

    def do_login(self):
        self.login.go().login(self.username, self.password)

        error = self.page.get_error() if self.login.is_here() else False

        if error:
            raise BrowserIncorrectPassword(error)

    @need_login
    def get_accounts_list(self):
        if not self.accounts:
            self.accounts = list(self.movements.go().iter_accounts())

        for account in self.accounts:
            account.owner_type = self.owner_type
            yield account

    @need_login
    def get_history(self, account):
        if account._data:
            return self.open(account._url, data=account._data).page.iter_history()
        return self.movements.go().iter_history()

    @need_login
    def get_profile(self):
        return self.profile.go().get_profile()

    def get_coming(self, account):
        raise NotImplementedError()

    def get_investment(self, account):
        raise NotImplementedError()


class LCLEspaceProBrowser(LCLEnterpriseBrowser):
    BASEURL = 'https://espacepro.secure.lcl.fr'

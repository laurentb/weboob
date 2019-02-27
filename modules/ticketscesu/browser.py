# -*- coding: utf-8 -*-

# Copyright(C) 2019      Antoine BOSSY
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

from __future__ import unicode_literals


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import ActionNeeded

from .pages import AccountsPage, LoginPage, ProfilePage


class TicketCesuBrowser(LoginBrowser):
    BASEURL = 'https://ebeneficiaire.cesu-as.fr'

    login_page = URL('/login.aspx', LoginPage)
    profile_page = URL('/customerManagement/ProfileManagement.aspx', ProfilePage)
    accounts_page = URL('/PaymentManagement/PaymentAccountInfoFullDemat.aspx', AccountsPage)


    def do_login(self):
        self.login_page.go().login(login=self.username, password=self.password)

        if self.profile_page.is_here():
            raise ActionNeeded('Please agree CGU on the CESU website.')

    @need_login
    def get_accounts(self):
        return self.accounts_page.go().get_accounts()

    @need_login
    def get_history(self, id):
        accounts = self.get_accounts()

        account = None
        for acc in accounts:
            if acc.id == id:
                account = acc

        if account and self.accounts_page.is_here():
            self.page.go_to_transaction_page(account._page)
            return self.page.get_transactions()

        return []

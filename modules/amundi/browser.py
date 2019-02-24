# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from .pages import LoginPage, AccountsPage, AccountHistoryPage
from weboob.browser import URL, LoginBrowser, need_login
from weboob.tools.json import json
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.exceptions import ClientError


class AmundiBrowser(LoginBrowser):
    TIMEOUT = 120.0

    login = URL(r'authenticate', LoginPage)
    authorize = URL(r'authorize', LoginPage)
    accounts = URL(r'api/individu/positionFonds\?flagUrlFicheFonds=true&inclurePositionVide=false', AccountsPage)
    account_history = URL(r'api/individu/operations\?valeurExterne=false&filtreStatutModeExclusion=false&statut=CPTA', AccountHistoryPage)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        try:
            self.login.go(data=json.dumps({'username': self.username, 'password': self.password}),
                          headers={'Content-Type': 'application/json;charset=UTF-8'})
            self.token = self.authorize.go().get_token()
        except ClientError:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        return (self.accounts.go(headers={'X-noee-authorization': ('noeprd %s' % self.token)})
                             .iter_accounts())

    @need_login
    def iter_investments(self, account):
        return (self.accounts.go(headers={'X-noee-authorization': ('noeprd %s' % self.token)})
                             .iter_investments(account_id=account.id))

    @need_login
    def iter_history(self, account):
        return (self.account_history.go(headers={'X-noee-authorization': ('noeprd %s' % self.token)})
                                    .iter_history(account=account))


class EEAmundi(AmundiBrowser):
    BASEURL = 'https://www.amundi-ee.com/psf/'

class TCAmundi(AmundiBrowser):
    BASEURL = 'https://epargnants.amundi-tc.com/psf/'

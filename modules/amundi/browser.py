# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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

    def prepare_request(self, req):
        """
        Amundi uses TLS v1.0.
        """
        preq = super(AmundiBrowser, self).prepare_request(req)
        conn = self.session.adapters['https://'].get_connection(preq.url)
        try:
            conn.ssl_version = ssl.PROTOCOL_TLS
        except AttributeError:
            conn.ssl_version = ssl.PROTOCOL_TLSv1
        return preq

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

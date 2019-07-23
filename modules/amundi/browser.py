# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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

from .pages import LoginPage, AccountsPage, AccountHistoryPage
from weboob.browser import URL, LoginBrowser, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.exceptions import ClientError
from weboob.capabilities.base import empty


class AmundiBrowser(LoginBrowser):
    TIMEOUT = 120.0

    login = URL(r'authenticate', LoginPage)
    authorize = URL(r'authorize', LoginPage)
    accounts = URL(r'api/individu/positionFonds\?flagUrlFicheFonds=true&inclurePositionVide=false', AccountsPage)
    account_history = URL(r'api/individu/operations\?valeurExterne=false&filtreStatutModeExclusion=false&statut=CPTA', AccountHistoryPage)

    def do_login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            self.login.go(json=data)
            self.token = self.authorize.go().get_token()
        except ClientError:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        headers = {'X-noee-authorization': 'noeprd %s' % self.token}
        self.accounts.go(headers=headers)
        company_name = self.page.get_company_name()
        if empty(company_name):
            self.logger.warning('Could not find the company name for these accounts.')
        for account in self.page.iter_accounts():
            account.company_name = company_name
            yield account

    @need_login
    def iter_investment(self, account):
        headers = {'X-noee-authorization': 'noeprd %s' % self.token}
        self.accounts.go(headers=headers)
        for inv in self.page.iter_investments(account_id=account.id):
            yield inv

    @need_login
    def iter_history(self, account):
        headers = {'X-noee-authorization': 'noeprd %s' % self.token}
        self.account_history.go(headers=headers)
        for tr in self.page.iter_history(account=account):
            yield tr


class EEAmundi(AmundiBrowser):
    BASEURL = 'https://www.amundi-ee.com/psf/'


class TCAmundi(AmundiBrowser):
    BASEURL = 'https://epargnants.amundi-tc.com/psf/'

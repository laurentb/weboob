# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, need_login, URL
from weboob.capabilities.bank import Investment

from .pages import LoginPage, AccountsPage, AccountPage, InvestPage


class NaloBrowser(LoginBrowser):
    BASEURL = 'https://nalo.fr'

    login = URL(r'/api/v1/login', LoginPage)
    accounts = URL(r'/api/v1/projects/mine/without_details', AccountsPage)
    history = URL(r'/api/v1/projects/(?P<id>\d+)/history')
    account = URL(r'/api/v1/projects/(?P<id>\d+)', AccountPage)
    invests = URL(r'https://app.nalo.fr/scripts/data/data.json', InvestPage)

    token = None

    def do_login(self):
        self.login.go(json={
            'email': self.username,
            'password': self.password,
            'userToken': False,
        })
        self.token = self.page.get_token()

    def build_request(self, *args, **kwargs):
        if 'json' in kwargs:
            kwargs.setdefault('headers', {})['Accept'] = 'application/json'
        if self.token:
            kwargs.setdefault('headers', {})['Authorization'] = 'Token %s' % self.token
        return super(NaloBrowser, self).build_request(*args, **kwargs)

    @need_login
    def iter_accounts(self):
        self.accounts.go()
        return self.page.iter_accounts()

    @need_login
    def iter_history(self, account):
        self.history.go(id=account.id)
        return self.page.iter_history()

    @need_login
    def iter_investment(self, account):
        self.account.go(id=account.id)
        key = self.page.get_invest_key()

        self.invests.go()
        data = self.page.get_invest(*key)
        for item in data:
            inv = Investment()
            inv.code = item['isin']
            inv.label = item['name']
            inv.portfolio_share = item['share']
            inv.valuation = account.balance * inv.portfolio_share
            yield inv

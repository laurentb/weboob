# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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
from weboob.exceptions import  BrowserIncorrectPassword
from .pages import (
    LoginPage, NewAccountsPage, OperationsListPage, OperationPage,
)


class CmesBrowserNew(LoginBrowser):
    BASEURL = 'https://www.cic-epargnesalariale.fr'

    login = URL('r(?P<client_space>.*)fr/identification/authentification.html', LoginPage)

    accounts = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/mon-epargne/situation-financiere-detaillee/index.html',
                   r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/tableau-de-bord/index.html',
                   NewAccountsPage)

    operations_list = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/operations/index.html',
                          OperationsListPage)

    operation = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/operations/consulter-une-operation/index.html\?param_=(?P<idx>\d+)',
                    OperationPage)

    client_space = 'espace-client/'

    def __init__(self, username, password, website, subsite="", *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.username = username
        self.password = password
        self.subsite = subsite

    @property
    def logged(self):
        return 'IdSes' in self.session.cookies

    def do_login(self):
        self.login.go(client_space=self.client_space)
        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        self.accounts.go(subsite=self.subsite, client_space=self.client_space)
        return self.page.iter_accounts()

    @need_login
    def iter_investment(self, account):
        self.accounts.stay_or_go(subsite=self.subsite, client_space=self.client_space)
        return self.page.iter_investment(account=account)

    @need_login
    def iter_history(self, account):
        self.operations_list.stay_or_go(subsite=self.subsite, client_space=self.client_space)
        for idx in self.page.get_operations_idx():
            tr = self.operation.go(subsite=self.subsite, client_space=self.client_space, idx=idx).get_transaction()
            if account.label == tr._account_label:
                yield tr

    @need_login
    def iter_pocket(self, account):
        for inv in self.iter_investment(account=account):
            for pocket in self.page.iter_pocket(inv=inv):
                yield pocket

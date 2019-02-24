# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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

from __future__ import unicode_literals

from datetime import date, timedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import AccountNotFound
from weboob.tools.compat import basestring

from .pages import LoginPage, AccountsPage, HistoryPage


__all__ = ['BNPCompany']


class BNPCompany(LoginBrowser):
    BASEURL = 'https://secure1.entreprises.bnpparibas.net'

    login = URL('/sommaire/jsp/identification.jsp', LoginPage)
    accounts = URL('/NCCPresentationWeb/e10_soldes/liste_soldes.do', AccountsPage)
    history = URL('/NCCPresentationWeb/e11_releve_op/listeOperations.do', HistoryPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()
        self.login.go()
        self.login.go()
        assert self.login.is_here()

        self.page.login(self.username, self.password)


    @need_login
    def iter_accounts(self):
        self.accounts.go()
        return self.page.iter_accounts()

    @need_login
    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    def get_transactions(self, id_account, typeReleve, dateMin, dateMax='null'):
        self.open('https://secure1.entreprises.bnpparibas.net/NCCPresentationWeb/e11_releve_op/init.do?e10=true')
        params = {}
        params['identifiant'] = id_account
        params['typeSole'] = 'C'
        params['typeReleve'] = typeReleve
        params['typeDate'] = 'O'
        params['ajax'] = 'true'
        params['dateMin'] = dateMin
        params['dateMax'] = dateMax
        self.history.go(params=params)
        return self.page.iter_history()

    @need_login
    def iter_history(self, account):
        return self.get_transactions(account.id,
                                'Comptable',
                                (date.today() - timedelta(days=90)).strftime('%Y%m%d'),
                                date.today().strftime('%Y%m%d'))

    @need_login
    def iter_coming_operations(self, account):
        return self.get_transactions(account.id,
                                'Previsionnel',
                                (date.today().strftime('%Y%m%d')))

    @need_login
    def iter_investment(self, account):
        raise NotImplementedError()

    @need_login
    def get_transfer_accounts(self):
        raise NotImplementedError()

    @need_login
    def transfer(self, account, to, amount, reason):
        raise NotImplementedError()

    @need_login
    def iter_threads(self):
        raise NotImplementedError()

    @need_login
    def get_thread(self, thread):
        raise NotImplementedError()

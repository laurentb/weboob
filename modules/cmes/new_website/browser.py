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


from weboob.browser import URL, need_login
from ..browser import CmesBrowser
from .pages import (
    NewAccountsPage, OperationsListPage, OperationPage
)


class CmesBrowserNew(CmesBrowser):

    accounts = URL(r'(?P<subsite>.*)espace-client/fr/epargnants/mon-epargne/situation-financiere-detaillee/index.html',
                   r'(?P<subsite>.*)espace-client/fr/epargnants/tableau-de-bord/index.html',
                   NewAccountsPage)

    operations_list = URL(r'(?P<subsite>.*)espace-client/fr/epargnants/operations/index.html',
                          OperationsListPage)

    operation = URL(r'(?P<subsite>.*)espace-client/fr/epargnants/operations/consulter-une-operation/index.html\?param_=(?P<idx>\d+)',
                    OperationPage)

    @need_login
    def iter_investment(self, account):
        return self.accounts.stay_or_go(subsite=self.subsite).iter_investment(account=account)

    @need_login
    def iter_history(self, account):
        self.operations_list.stay_or_go(subsite=self.subsite)
        for idx in self.page.get_operations_idx():
            tr = self.operation.go(subsite=self.subsite, idx=idx).get_transaction()
            if account.label == tr._account_label:
                yield tr

    @need_login
    def iter_pocket(self, account):
        for inv in self.iter_investment(account=account):
            for pocket in self.page.iter_pocket(inv=inv):
                yield pocket

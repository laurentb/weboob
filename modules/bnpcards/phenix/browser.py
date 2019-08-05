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


from weboob.exceptions import BrowserIncorrectPassword, BrowserPasswordExpired
from weboob.browser import LoginBrowser, URL, need_login

from .pages import (
    LoginPage, DashboardPage, TransactionPage, TransactionCSV,
    PasswordExpiredPage,
)

__all__ = ['BnpcartesentreprisePhenixBrowser']


class BnpcartesentreprisePhenixBrowser(LoginBrowser):
    BASEURL = 'https://corporatecards.bnpparibas.com'

    login_cas = URL(r'https://cartesentreprise-oidc.phenix.bnpparibas/login', LoginPage)
    login = URL(r'/login', LoginPage)
    dashboard = URL(r'/group/bddf/dashboard', DashboardPage)
    transaction_csv = URL(
        r'/group/bddf/transactions\?p_p_id=Phenix_Transactions_Portlet_INSTANCE_(?P<instance_id1>.*)'
        r'&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=/transaction/export&p_p_cacheability=cacheLevelPage&'
        r'_Phenix_Transactions_Portlet_INSTANCE_(?P<instance_id2>.*)_MVCResourceCommand=/transaction/export',
        TransactionCSV
    )
    transactions_page = URL(r'/group/bddf/transactions', TransactionPage)
    password_expired = URL(r'https://corporatecards.bnpparibas.com/group/bddf/mot-de-passe-expire', PasswordExpiredPage)

    def __init__(self, website, *args, **kwargs):
        super(BnpcartesentreprisePhenixBrowser, self).__init__(*args, **kwargs)
        self.website = website

    def do_login(self):
        self.login_cas.go()
        self.page.login(self.username, self.password)
        if not(self.page.is_logged()):
            raise BrowserIncorrectPassword(self.page.get_error_message())
        self.dashboard.go()
        if self.password_expired.is_here():
            raise BrowserPasswordExpired(self.page.get_error_message())

    @need_login
    def iter_accounts(self):
        self.dashboard.go()
        for account in self.page.iter_accounts():
            self.location(account.url)
            yield self.page.fill_account(obj=account)

    @need_login
    def get_transactions(self, account):
        self.dashboard.stay_or_go()
        self.location(account.url)
        self.transactions_page.go()
        instance_id = self.page.get_instance_id()
        page_csv = self.transaction_csv.open(method="POST", instance_id1=instance_id, instance_id2=instance_id)
        for tr in page_csv.iter_history():
            yield tr

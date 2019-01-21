# -*- coding: utf-8 -*-

# Copyright(C) 2019      Damien Cassou
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

import datetime

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, HomePage, AccountsPage, TransactionsPage

def next_week_string():
    return (datetime.date.today() + datetime.timedelta(weeks=1)).strftime("%Y-%m-%d")

class NefBrowser(LoginBrowser):
    BASEURL = 'https://espace-client.lanef.com'

    home = URL('/templates/home.cfm', HomePage)
    main = URL('/templates/main.cfm', HomePage)
    download = URL(r'/templates/account/accountActivityListDownload.cfm\?viewMode=CSV&orderBy=TRANSACTION_DATE_DESCENDING&page=1&startDate=2016-01-01&endDate=%s&showBalance=true&AccNum=(?P<account_id>.*)' % next_week_string(), TransactionsPage)
    login = URL('/templates/logon/logon.cfm', LoginPage)

    def do_login(self):
        self.login.stay_or_go()

        self.page.login(self.username, self.password)

        if not self.home.is_here():
            raise BrowserIncorrectPassword('Error logging in')

    @need_login
    def iter_accounts_list(self):
        response = self.main.open(data={
            'templateName': 'account/accountList.cfm'
        })

        page = AccountsPage(self, response)
        return page.get_items()

    @need_login
    def iter_transactions_list(self, account):
        return self.download.go(account_id=account.id).iter_history()

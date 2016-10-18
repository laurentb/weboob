# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.exceptions import  BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login

from .pages import LoginPage, AccountsPage, InvestmentPage, HistoryPage


class CmesBrowser(LoginBrowser):
    login = URL('identification/default.cgi', LoginPage)
    accounts = URL('espace/devbavoirs.aspx\?mode=net&menu=cpte$', AccountsPage)
    investment = URL('.*GoPositionsParFond.*', InvestmentPage)
    history = URL('espace/ListeOperations.asp\?TypeOperation_=T',
                  'espace/OpeDetail.asp', HistoryPage)

    def __init__(self, website, username, password, *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.username = username
        self.password = password

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        return self.accounts.stay_or_go().iter_accounts()

    @need_login
    def iter_investment(self, account):
        link = self.accounts.stay_or_go().get_investment_link()
        if link:
            return self.location(link).page.iter_investment()

    @need_login
    def iter_history(self, account):
        return self.history.stay_or_go().iter_history()

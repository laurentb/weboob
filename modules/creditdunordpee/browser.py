# -*- coding: utf-8 -*-

# Copyright(C) 2016      Bezleputh
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


from weboob.browser import LoginBrowser, need_login, URL
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser
from weboob.capabilities.bank import Account
from .pages import LoginPage, HomePage, AvoirPage, HistoryPage


class CreditdunordpeeBrowser(LoginBrowser):
    BASEURL = 'https://salaries.pee.credit-du-nord.fr'
    home = URL('/?/portal/fr/salarie-cdn/', HomePage)
    login = URL('/portal/login', LoginPage)
    avoir = URL(u'/portal/salarie-cdn/monepargne/mesavoirs', AvoirPage)
    history = URL(u'/portal/salarie-cdn/operations/consulteroperations\?scenario=ConsulterOperationsEffectuees',
                  HistoryPage)

    def do_login(self):
        self.home.stay_or_go()
        passwd = self.page.get_coded_passwd(self.password)
        d = {'initialURI': "/portal/fr/salarie-cdn/",
             'password': passwd,
             'username': self.username}

        self.login.go(data=d)

        if not (self.home.is_here() and self.page.is_logged()):
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        account = Account(self.username)
        return iter([self.avoir.go().get_account(obj=account)])

    @need_login
    def get_history(self):
        transactions = list(self.history.go().get_history(date_guesser=LinearDateGuesser()))
        transactions.sort(key=lambda tr: tr.date, reverse=True)
        return transactions

    @need_login
    def iter_investment(self):
        return self.avoir.go().iter_investment()

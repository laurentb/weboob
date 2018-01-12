# -*- coding: utf-8 -*-

# Copyright(C) 2015 Romain Bignon
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


import time

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import AccountNotFound
from weboob.capabilities.base import find_object, NotAvailable


from .pages import LoginPage, MenuPage, AccountsPage, HistoryPage, IbanPage, ErrorPage


__all__ = ['DelubacBrowser']


class DelubacBrowser(LoginBrowser):
    BASEURL = 'https://e.delubac.com'

    home = URL('/es@b/fr/esab.jsp')
    login = URL('/es@b/fr/codeident.jsp',
                '/es@b/servlet/internet0.ressourceWeb.servlet.Login', LoginPage)
    menu = URL('/es@b/fr/menuConnecte1.jsp\?c&deploye=false&pulseMenu=false&styleLien=false&dummyDate=(?P<date>.*)', MenuPage)
    accounts = URL('/es@b/servlet/internet0.ressourceWeb.servlet.EsabServlet.*', AccountsPage)
    history = URL('/es@b/servlet/internet0.ressourceWeb.servlet.ListeDesMouvementsServlet.*', HistoryPage)
    error = URL('/es@b/servlet/internet0.ressourceWeb.servlet.*', ErrorPage)
    iban = URL('/es@b/fr/rib.jsp', IbanPage)

    def do_login(self):
        self.home.go()
        self.login.go()

        self.page.login(self.username, self.password)

        if self.page.incorrect_auth:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        self.menu.go(date=int(time.time()*1000))
        self.location(self.page.accounts_url)
        for account in self.page.get_list():
            self.location(account._rib_link)
            account.iban = self.page.get_iban()
            yield account

    @need_login
    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    @need_login
    def iter_history(self, account):
        if account._link is not NotAvailable:
            self.location(account._link)
        else:
            return []

        if self.error.is_here():
            return iter([])
        return self.page.get_transactions()

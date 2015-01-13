# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser

from .pages import LoginPage, LoginErrorPage, AvoirPage, OperationsTraiteesPage, OperationsFuturesPage


__all__ = ['GroupamaesBrowser']


class GroupamaesBrowser(LoginBrowser):
    BASEURL = 'https://www.gestion-epargne-salariale.fr'

    login = URL('/groupama-es/fr/index.html', LoginPage)
    login_error = URL('/groupama-es/fr/identification/default.cgi', LoginErrorPage)
    avoir = URL('/groupama-es/fr/espace/devbavoirs.aspx.*', AvoirPage)
    operations_traitees = URL('/groupama-es/fr/espace/ListeOperations.asp\?TypeOperation=T', OperationsTraiteesPage)
    operations_futures = URL('/groupama-es/fr/espace/ListeOperations.asp\?TypeOperation=E', OperationsFuturesPage)

    def do_login(self):
        self.login.stay_or_go()

        self.page.login(self.username, self.password)

        if not self.page.logged or self.login_error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        return self.avoir.stay_or_go().iter_accounts()

    @need_login
    def get_history(self):
        transactions = list(self.operations_traitees.go().get_history(date_guesser=LinearDateGuesser()))
        transactions.sort(key=lambda tr: tr.rdate, reverse=True)
        return transactions

    @need_login
    def get_coming(self):
        transactions = list(self.operations_futures.go().get_list(date_guesser=LinearDateGuesser()))
        transactions.sort(key=lambda tr: tr.rdate, reverse=True)
        return transactions

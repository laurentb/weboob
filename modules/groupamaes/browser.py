# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import LoginPage, LoginErrorPage, GroupamaesPage, GroupamaesPocketPage


__all__ = ['GroupamaesBrowser']


class GroupamaesBrowser(LoginBrowser):
    BASEURL = 'https://www.gestion-epargne-salariale.fr'

    login = URL('/groupama-es/espace-client/fr/identification/authentification.html', LoginPage)
    login_error = URL('/groupama-es/fr/identification/default.cgi', LoginErrorPage)
    groupamaes_page = URL('/groupama-es/fr/espace/devbavoirs.aspx\?mode=net&menu=cpte(?P<page>.*)', GroupamaesPage)
    groupamaes_pocket = URL('/groupama-es/fr/espace/devbavoirs.aspx\?_tabi=C&a_mode=net&a_mode=net&menu=cpte(?P<page>.*)', GroupamaesPocketPage)

    def do_login(self):
        self.login.stay_or_go()

        self.page.login(self.username, self.password)

        if not self.page.logged or self.login_error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        return self.groupamaes_page.stay_or_go(page='&page=situglob').iter_accounts()

    @need_login
    def get_history(self):
        transactions = list(self.groupamaes_page.go(page='&_pid=MenuOperations&_fid=GoOperationsTraitees').get_history(date_guesser=LinearDateGuesser()))
        transactions = sorted_transactions(transactions)
        return transactions

    @need_login
    def get_coming(self):
        transactions = list(self.groupamaes_page.go(page='&_pid=OperationsTraitees&_fid=GoWaitingOperations').get_history(date_guesser=LinearDateGuesser(), coming=True))
        transactions = sorted_transactions(transactions)
        return transactions

    @need_login
    def iter_investment(self, account):
        return self.groupamaes_pocket.go(page='&_pid=SituationParPlan&_fid=GoPositionsDetaillee').iter_investment(account.label)

    @need_login
    def iter_pocket(self, account):
        return self.groupamaes_pocket.go(page='&_pid=SituationParPlan&_fid=GoPositionsDetaillee').iter_pocket(account.label)

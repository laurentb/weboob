# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from .pages import LoginPage, AccountsPage, InvestmentPage, HistoryPage


class AvivaBrowser(LoginBrowser):
    BASEURL = 'https://www.aviva.fr/espaceclient/'

    login = URL('MonCompte/Connexion', LoginPage)
    accounts = URL('Accueil/Synthese-Contrats', AccountsPage)
    investment = URL('contrat/epargne/', InvestmentPage)
    history = URL('contrat/getOperations', HistoryPage)

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        return self.accounts.stay_or_go().iter_accounts()

    @need_login
    def iter_investment(self, account):
        return self.location(account._link).page.iter_investment()

    @need_login
    def iter_history(self, account):
        link = self.location(account._link).page.get_history_link()
        return self.location(link).page.iter_history()

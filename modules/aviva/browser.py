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
from weboob.capabilities.base import empty
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded

from .pages import (
    LoginPage, AccountsPage, InvestmentPage, HistoryPage,
    ActionNeededPage, InvestDetail
)


class AvivaBrowser(LoginBrowser):
    BASEURL = 'https://www.aviva.fr'

    login = URL('/espaceclient/MonCompte/Connexion',
                '/espaceclient/conventions/acceptation', LoginPage)
    accounts = URL('/espaceclient/Accueil/Synthese-Contrats', AccountsPage)
    investment = URL(r'/espaceclient/contrat/epargne/-(?P<page_id>[0-9]{10})', InvestmentPage)
    history = URL(r'/espaceclient/contrat/getOperations\?param1=(?P<history_token>.*)', HistoryPage)
    action_needed = URL(r'/espaceclient/coordonnees/detailspersonne\?majcontacts=true', ActionNeededPage)
    invest_detail = URL(r'https://aviva.sixtelekurs.fr/.*', InvestDetail)

    def do_login(self):
        if not self.password.isdigit():
            raise BrowserIncorrectPassword()
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            if "acceptation" in self.url:
                raise ActionNeeded(u'Veuillez accepter les conditions générales d\'utilisation sur le site.')
            else:
                raise BrowserIncorrectPassword(u'L\'identifiant ou le mot de passe est incorrect.')

    @need_login
    def iter_accounts(self):
        return self.accounts.stay_or_go().iter_accounts()

    @need_login
    def iter_investment(self, account):
        return self.location(account._link).page.iter_investment()

    @need_login
    def iter_history(self, account):
        if empty(account._link):
            raise NotImplementedError()

        self.location(account._link)
        self.location(self.page.get_history_link())
        assert self.history.is_here()         # must be here
        return self.page.iter_history()

    def get_subscription_list(self):
        return iter([])

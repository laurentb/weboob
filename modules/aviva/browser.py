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

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import empty, NotAvailable
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded, BrowserHTTPError
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages.detail_pages import (
    LoginPage, InvestmentPage, HistoryPage, ActionNeededPage, InvestDetailPage, PrevoyancePage, ValidationPage,
)

from .pages.account_page import AccountsPage


class AvivaBrowser(LoginBrowser):
    BASEURL = 'https://www.aviva.fr'

    validation = URL(r'/espaceclient/conventions/acceptation\?backurl=/espaceclient/Accueil', ValidationPage)
    login = URL(r'/espaceclient/MonCompte/Connexion',
                r'/espaceclient/conventions/acceptation', LoginPage)
    accounts = URL(r'/espaceclient/Accueil/Synthese-Contrats', AccountsPage)
    investment = URL(r'/espaceclient/contrat/epargne/-(?P<page_id>[0-9]{10})', InvestmentPage)
    prevoyance = URL(r'/espaceclient/contrat/prevoyance/-(?P<page_id>[0-9]{10})', PrevoyancePage)
    history = URL(r'/espaceclient/contrat/getOperations\?param1=(?P<history_token>.*)', HistoryPage)
    action_needed = URL(r'/espaceclient/coordonnees/detailspersonne\?majcontacts=true', ActionNeededPage)
    invest_detail = URL(r'http://aviva.sixtelekurs.fr/opcvm.hts.*', InvestDetailPage)

    def do_login(self):
        self.login.go().login(self.username, self.password)
        if self.login.is_here():
            if "acceptation" in self.url:
                raise ActionNeeded('Veuillez accepter les conditions générales d\'utilisation sur le site.')
            else:
                raise BrowserIncorrectPassword('L\'identifiant ou le mot de passe est incorrect.')

    @need_login
    def iter_accounts(self):
        self.accounts.stay_or_go()
        for account in self.page.iter_accounts():
            # Request to account details sometimes returns a 500
            try:
                self.location(account.url)
                if not self.investment.is_here() or self.page.unavailable_details():
                    # We don't scrape insurances, guarantees, health contracts
                    # and accounts with unavailable balances
                    continue
                self.page.fill_account(obj=account)
                yield account
            except BrowserHTTPError:
                self.logger.warning('Could not get the account details: account %s will be skipped', account.id)

    @need_login
    def iter_investment(self, account):
        # Request to account details sometimes returns a 500
        try:
            self.location(account.url)
        except BrowserHTTPError:
            self.logger.warning('Could not get the account investments for account %s', account.id)
            return
        for inv in self.page.iter_investment():
            if not empty(inv.code):
                # Fill investments details with ISIN code
                params = {'isin': inv.code}
                self.invest_detail.go(params=params)
                self.page.fill_investment(obj=inv)
            else:
                inv.unitprice = inv.diff_percent = inv.description = NotAvailable
            yield inv

    @need_login
    def iter_history(self, account):
        if empty(account.url):
            # An account should always have a link to the details
            raise NotImplementedError()
        try:
            self.location(account.url)
        except BrowserHTTPError:
            self.logger.warning('Could not get the history for account %s', account.id)
            return

        history_link = self.page.get_history_link()

        if not history_link:
            # accounts don't always have an history_link
            raise NotImplementedError()

        self.location(history_link)
        assert self.history.is_here()
        result = []
        result.extend(self.page.iter_versements())
        result.extend(self.page.iter_arbitrages())
        return sorted_transactions(result)

    def get_subscription_list(self):
        return []

# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

import json
import time
from datetime import date
from decimal import Decimal

from weboob.capabilities.bank import Account, Investment
from weboob.browser import LoginBrowser, need_login, URL
from weboob.capabilities.base import find_object
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import (
    HomePage, LoginPage, UniversePage,
    TokenPage, MoveUniversePage, SwitchPage,
    LoansPage, AccountsPage, IbanPage, LifeInsurancesPage,
    SearchPage, ProfilePage, EmailsPage, ErrorPage,
)

__all__ = ['BredBrowser']


class BredBrowser(LoginBrowser):
    BASEURL = 'https://www.bred.fr'

    home =              URL('/$', HomePage)
    login =             URL('/transactionnel/Authentication', LoginPage)
    error =             URL('.*gestion-des-erreurs/erreur-pwd',
                            '.*gestion-des-erreurs/opposition',
                            '/pages-gestion-des-erreurs/erreur-technique',
                            '/pages-gestion-des-erreurs/message-tiers-oppose', ErrorPage)
    universe =          URL('/transactionnel/services/applications/menu/getMenuUnivers', UniversePage)
    token =             URL('/transactionnel/services/rest/User/nonce\?random=(?P<timestamp>.*)', TokenPage)
    move_universe =     URL('/transactionnel/services/applications/listes/(?P<key>.*)/default', MoveUniversePage)
    switch =            URL('/transactionnel/services/rest/User/switch', SwitchPage)
    loans =             URL('/transactionnel/services/applications/prets/liste', LoansPage)
    accounts =          URL('/transactionnel/services/rest/Account/accounts', AccountsPage)
    iban =              URL('/transactionnel/services/rest/Account/account/(?P<number>.*)/iban', IbanPage)
    life_insurances =   URL('/transactionnel/services/applications/avoirsPrepar/getAvoirs', LifeInsurancesPage)
    search =            URL('/transactionnel/services/applications/operations/getSearch/', SearchPage)
    profile =           URL('/transactionnel/services/rest/User/user', ProfilePage)
    emails =            URL('/transactionnel/services/applications/gestionEmail/getAdressesMails', EmailsPage)

    def __init__(self, accnum, login, password, *args, **kwargs):
        kwargs['username'] = login
        # Bred only use first 8 char (even if the password is set to be bigger)
        # The js login form remove after 8th char. No comment.
        kwargs['password'] = password[:8]
        super(BredBrowser, self).__init__(*args, **kwargs)

        self.accnum = accnum
        self.universes = None
        self.current_univers = None

    def do_login(self):
        if 'hsess' not in self.session.cookies:
            self.home.go()  # set session token
            assert 'hsess' in self.session.cookies, "Session token not correctly set"

        # hard-coded authentication payload
        data = dict(identifiant=self.username, password=self.password)
        cookies = {k: v for k, v in self.session.cookies.items() if k in ('hsess', )}
        self.session.cookies.update(cookies)
        self.login.go(data=data)

    @need_login
    def get_universes(self):
        """Get universes (particulier, pro, etc)"""
        self.get_and_update_bred_token()
        self.universe.go(headers={'Accept': 'application/json'})

        return self.page.get_universes()

    def get_and_update_bred_token(self):
        timestamp = int(time.time() * 1000)
        x_token_bred = self.token.go(timestamp=timestamp).get_content()
        self.session.headers.update({'X-Token-Bred': x_token_bred, })  # update headers for session
        return {'X-Token-Bred': x_token_bred, }

    def move_to_univers(self, univers):
        if univers == self.current_univers:
            return
        self.move_universe.go(key=univers)
        self.get_and_update_bred_token()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.switch.go(
            data=json.dumps({'all': 'false', 'univers': univers}),
            headers=headers,
        )
        self.current_univers = univers

    @need_login
    def get_accounts_list(self):
        accounts = []
        for universe_key in self.get_universes():
            self.move_to_univers(universe_key)
            accounts.extend(self.get_list())
            accounts.extend(self.get_loans_list())
            accounts.extend(self.get_life_insurance_list(accounts))

        return sorted(accounts, key=lambda x: x._univers)

    @need_login
    def get_loans_list(self):
        self.loans.go()
        return self.page.iter_loans(current_univers=self.current_univers)

    @need_login
    def get_list(self):
        self.accounts.go()
        for acc in self.page.iter_accounts(accnum=self.accnum, current_univers=self.current_univers):
            if acc.type == Account.TYPE_CHECKING:
                self.iban.go(number=acc._number)
                self.page.set_iban(account=acc)
            yield acc

    @need_login
    def get_life_insurance_list(self, accounts):
        accounts = self.get_list()

        self.life_insurances.go()

        for ins in self.page.iter_life_insurances(current_univers=self.current_univers):
            ins.parent = find_object(accounts, _number=ins._number, type=Account.TYPE_CHECKING)
            yield ins

    @need_login
    def _make_api_call(self, account, start_date, end_date, offset, max_length=50):
        HEADERS = {
            'Accept': "application/json",
            'Content-Type': 'application/json',
        }
        HEADERS.update(self.get_and_update_bred_token())
        call_payload = {
            "account": account._number,
            "poste": account._nature,
            "sousPoste": account._codeSousPoste or '00',
            "devise": account.currency,
            "fromDate": start_date.strftime('%Y-%m-%d'),
            "toDate": end_date.strftime('%Y-%m-%d'),
            "from": offset,
            "size": max_length,  # max length of transactions
            "search": "",
            "categorie": "",
        }
        self.search.go(data=json.dumps(call_payload), headers=HEADERS)
        return self.page.get_transaction_list()

    @need_login
    def get_history(self, account, coming=False):
        if account.type is Account.TYPE_LOAN or not account._consultable:
            raise NotImplementedError()

        if account._univers != self.current_univers:
            self.move_to_univers(account._univers)

        today = date.today()
        seen = set()
        offset = 0
        next_page = True
        while next_page:
            operation_list = self._make_api_call(
                account=account,
                start_date=date(day=1, month=1, year=2000), end_date=date.today(),
                offset=offset, max_length=50,
            )

            transactions = self.page.iter_history(account=account, operation_list=operation_list, seen=seen, today=today, coming=coming)

            # Transactions are unsorted
            for t in sorted_transactions(transactions):
                if coming == t._coming:
                    yield t
                elif coming and not t._coming:
                    # coming transactions are at the top of history
                    self.logger.debug('stopping coming after %s', t)
                    return

            next_page = len(transactions) == 50
            offset += 50

            # This assert supposedly prevents infinite loops,
            # but some customers actually have a lot of transactions.
            assert offset < 100000, 'the site may be doing an infinite loop'

    @need_login
    def get_investment(self, account):
        if account.type != Account.TYPE_LIFE_INSURANCE:
            raise NotImplementedError()

        if account._univers != self.current_univers:
            self.move_to_univers(account._univers)

        for invest in account._investments:
            inv = Investment()
            inv.label = invest['libelle'].strip()
            inv.code = invest['code']
            inv.valuation = Decimal(str(invest['montant']))
            yield inv

    @need_login
    def get_profile(self):
        self.get_universes()

        self.profile.go()
        profile = self.page.get_profile()

        self.emails.go()
        self.page.set_email(profile=profile)

        return profile

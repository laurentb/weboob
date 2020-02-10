# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

import json
import time
import operator
from datetime import date

from weboob.capabilities.bank import Account
from weboob.browser import LoginBrowser, need_login, URL
from weboob.capabilities.base import find_object
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .linebourse_browser import LinebourseAPIBrowser
from .pages import (
    HomePage, LoginPage, UniversePage,
    TokenPage, MoveUniversePage, SwitchPage,
    LoansPage, AccountsPage, IbanPage, LifeInsurancesPage,
    SearchPage, ProfilePage, EmailsPage, ErrorPage,
    ErrorCodePage, LinebourseLoginPage,
)

__all__ = ['BredBrowser']


class BredBrowser(LoginBrowser):
    BASEURL = 'https://www.bred.fr'

    LINEBOURSE_BROWSER = LinebourseAPIBrowser

    home = URL(r'/$', HomePage)
    login = URL(r'/transactionnel/Authentication', LoginPage)
    error = URL(r'.*gestion-des-erreurs/erreur-pwd',
                r'.*gestion-des-erreurs/opposition',
                r'/pages-gestion-des-erreurs/erreur-technique',
                r'/pages-gestion-des-erreurs/message-tiers-oppose', ErrorPage)
    universe = URL(r'/transactionnel/services/applications/menu/getMenuUnivers', UniversePage)
    token = URL(r'/transactionnel/services/rest/User/nonce\?random=(?P<timestamp>.*)', TokenPage)
    move_universe = URL(r'/transactionnel/services/applications/listes/(?P<key>.*)/default', MoveUniversePage)
    switch = URL(r'/transactionnel/services/rest/User/switch', SwitchPage)
    loans = URL(r'/transactionnel/services/applications/prets/liste', LoansPage)
    accounts = URL(r'/transactionnel/services/rest/Account/accounts', AccountsPage)
    iban = URL(r'/transactionnel/services/rest/Account/account/(?P<number>.*)/iban', IbanPage)
    linebourse_login = URL(r'/transactionnel/v2/services/applications/SSO/linebourse', LinebourseLoginPage)
    life_insurances = URL(r'/transactionnel/services/applications/avoirsPrepar/getAvoirs', LifeInsurancesPage)
    search = URL(r'/transactionnel/services/applications/operations/getSearch/', SearchPage)
    profile = URL(r'/transactionnel/services/rest/User/user', ProfilePage)
    emails = URL(r'/transactionnel/services/applications/gestionEmail/getAdressesMails', EmailsPage)
    error_code = URL(r'/.*\?errorCode=.*', ErrorCodePage)

    def __init__(self, accnum, login, password, *args, **kwargs):
        kwargs['username'] = login
        # Bred only use first 8 char (even if the password is set to be bigger)
        # The js login form remove after 8th char. No comment.
        kwargs['password'] = password[:8]
        super(BredBrowser, self).__init__(*args, **kwargs)

        self.accnum = accnum
        self.universes = None
        self.current_univers = None

        dirname = self.responses_dirname
        if dirname:
            dirname += '/bourse'

        self.weboob = kwargs['weboob']
        self.linebourse = self.LINEBOURSE_BROWSER(
            'https://www.linebourse.fr',
            logger=self.logger,
            responses_dirname=dirname,
            weboob=self.weboob,
            proxy=self.PROXIES,
        )
        # Some accounts are detailed on linebourse. The only way to know which is to go on linebourse.
        # The parameters to do so depend on the universe.
        self.linebourse_urls = {}
        self.linebourse_tokens = {}

    def do_login(self):
        if 'hsess' not in self.session.cookies:
            self.home.go()  # set session token
            assert 'hsess' in self.session.cookies, "Session token not correctly set"

        # hard-coded authentication payload
        data = dict(identifiant=self.username, password=self.password)
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

    def move_to_universe(self, univers):
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
            self.move_to_universe(universe_key)
            universe_accounts = []
            universe_accounts.extend(self.get_list())
            universe_accounts.extend(self.get_life_insurance_list(accounts))
            universe_accounts.extend(self.get_loans_list())
            linebourse_accounts = self.get_linebourse_accounts(universe_key)
            for account in universe_accounts:
                account._is_in_linebourse = False
                # Accound id looks like 'bred_account_id.folder_id'
                # We only want bred_account_id and we need to clean it to match it to linebourse IDs.
                account_id = account.id.strip('0').split('.')[0]
                for linebourse_account in linebourse_accounts:
                    if account_id in linebourse_account:
                        account._is_in_linebourse = True
            accounts.extend(universe_accounts)

        # Life insurances are sometimes in multiple universes, we have to remove duplicates
        unique_accounts = {account.id: account for account in accounts}
        return sorted(unique_accounts.values(), key=operator.attrgetter('_univers'))

    @need_login
    def get_linebourse_accounts(self, universe_key):
        self.move_to_universe(universe_key)
        if universe_key not in self.linebourse_urls:
            self.linebourse_login.go()
            if self.linebourse_login.is_here():
                linebourse_url = self.page.get_linebourse_url()
                if linebourse_url:
                    self.linebourse_urls[universe_key] = linebourse_url
                    self.linebourse_tokens[universe_key] = self.page.get_linebourse_token()
        if universe_key in self.linebourse_urls:
            self.linebourse.location(
                self.linebourse_urls[universe_key],
                data={'SJRToken': self.linebourse_tokens[universe_key]}
            )
            self.linebourse.session.headers['X-XSRF-TOKEN'] = self.linebourse.session.cookies.get('XSRF-TOKEN')
            params = {'_': '{}'.format(int(time.time() * 1000))}
            self.linebourse.account_codes.go(params=params)
            if self.linebourse.account_codes.is_here():
                return self.linebourse.page.get_accounts_list()
        return []

    @need_login
    def get_loans_list(self):
        self.loans.go()
        return self.page.iter_loans(current_univers=self.current_univers)

    @need_login
    def get_list(self):
        self.accounts.go()
        for acc in self.page.iter_accounts(accnum=self.accnum, current_univers=self.current_univers):
            yield acc

    @need_login
    def get_life_insurance_list(self, accounts):

        self.life_insurances.go()

        for ins in self.page.iter_lifeinsurances(univers=self.current_univers):
            ins.parent = find_object(accounts, _number=ins._parent_number, type=Account.TYPE_CHECKING)
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
        if account.type in (Account.TYPE_LOAN, Account.TYPE_LIFE_INSURANCE) or not account._consultable:
            raise NotImplementedError()

        if account._univers != self.current_univers:
            self.move_to_universe(account._univers)

        today = date.today()
        seen = set()
        offset = 0
        next_page = True
        end_date = date.today()
        last_date = None
        while next_page:
            if offset == 10000:
                offset = 0
                end_date = last_date
            operation_list = self._make_api_call(
                account=account,
                start_date=date(day=1, month=1, year=2000), end_date=end_date,
                offset=offset, max_length=50,
            )

            transactions = self.page.iter_history(account=account, operation_list=operation_list, seen=seen, today=today, coming=coming)

            transactions = sorted_transactions(transactions)
            if transactions:
                last_date = transactions[-1].date
            # Transactions are unsorted
            for t in transactions:
                if coming == t._coming:
                    yield t
                elif coming and not t._coming:
                    # coming transactions are at the top of history
                    self.logger.debug('stopping coming after %s', t)
                    return

            next_page = len(transactions) > 0
            offset += 50

            # This assert supposedly prevents infinite loops,
            # but some customers actually have a lot of transactions.
            assert offset < 100000, 'the site may be doing an infinite loop'

    @need_login
    def get_investment(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            for invest in account._investments:
                yield invest

        elif account.type in (Account.TYPE_PEA, Account.TYPE_MARKET):
            if 'Portefeuille Titres' in account.label:
                if account._is_in_linebourse:
                    if account._univers != self.current_univers:
                        self.move_to_universe(account._univers)
                    self.linebourse.location(
                        self.linebourse_urls[account._univers],
                        data={'SJRToken': self.linebourse_tokens[account._univers]}
                    )
                    self.linebourse.session.headers['X-XSRF-TOKEN'] = self.linebourse.session.cookies.get('XSRF-TOKEN')
                    for investment in self.linebourse.iter_investments(account.id.strip('0').split('.')[0]):
                        yield investment
                else:
                    raise NotImplementedError()
            else:
                # Compte espèces
                yield create_french_liquidity(account.balance)

        else:
            raise NotImplementedError()


    @need_login
    def get_profile(self):
        self.get_universes()

        self.profile.go()
        profile = self.page.get_profile()

        self.emails.go()
        self.page.set_email(profile=profile)

        return profile

    @need_login
    def fill_account(self, account, fields):
        if account.type == Account.TYPE_CHECKING and 'iban' in fields:
            self.iban.go(number=account._number)
            self.page.set_iban(account=account)

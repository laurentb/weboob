# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019 Romain Bignon
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

import re

from weboob.capabilities.bank import (
    Account,
)
from weboob.capabilities.base import find_object, empty, NotAvailable
from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword
from weboob.browser.exceptions import ServerError
from weboob.tools.capabilities.bank.iban import is_iban_valid

from .pages import (
    LoginPage, LoggedOutPage, KeypadPage, SecurityPage, ContractsPage, AccountsPage, AccountDetailsPage,
    IbanPage, HistoryPage, ProfilePage,
)


__all__ = ['CragrAPI']


class CragrAPI(LoginBrowser):
    login_page = URL(r'particulier/acceder-a-mes-comptes.html$', LoginPage)
    keypad = URL(r'particulier/acceder-a-mes-comptes.authenticationKeypad.json', KeypadPage)
    security_check = URL(r'particulier/acceder-a-mes-comptes.html/j_security_check', SecurityPage)
    logged_out = URL(r'.*', LoggedOutPage)

    contracts_page = URL(r'particulier/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)',
                         r'association/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)',
                         r'professionnel/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)', ContractsPage)

    accounts_page = URL(r'particulier/operations/synthese.html',
                        r'association/operations/synthese.html',
                        r'professionnel/operations/synthese.html', AccountsPage)

    account_details = URL(r'particulier/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)',
                          r'association/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)',
                          r'professionnel/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)', AccountDetailsPage)

    account_iban = URL(r'particulier/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json',
                       r'association/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json',
                       r'professionnel/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json', IbanPage)

    history_page = URL(r'particulier/operations/synthese/detail-comptes/jcr:content.n3.compte.infos.json',
                       r'association/operations/synthese/detail-comptes/jcr:content.n3.compte.infos.json',
                       r'professionnel/operations/synthese/detail-comptes/jcr:content.n3.compte.infos.json', HistoryPage)

    profile_page = URL(r'particulier/operations/synthese/jcr:content.npc.store.client.json',
                       r'association/operations/synthese/jcr:content.npc.store.client.json',
                       r'professionnel/operations/synthese/jcr:content.npc.store.client.json', ProfilePage)


    def __init__(self, website, *args, **kwargs):
        super(CragrAPI, self).__init__(*args, **kwargs)
        website = website.replace('.fr', '')
        self.region = re.sub('^m\.', 'www.credit-agricole.fr/', website)
        self.BASEURL = 'https://%s/' % self.region
        self.accounts_url = None

    def do_login(self):
        self.keypad.go()
        keypad_password = self.page.build_password(self.password[:6])
        keypad_id = self.page.get_keypad_id()
        assert keypad_password, 'Could not obtain keypad password'
        assert keypad_id, 'Could not obtain keypad id'

        self.login_page.go()
        # Get the form data to POST the security check:
        form = self.page.get_login_form(self.username, keypad_password, keypad_id)
        try:
            self.security_check.go(data=form)
        except ServerError as exc:
            # Wrongpass returns a 500 server error...
            error = exc.response.json().get('error')
            if error:
                message = error.get('message', '')
                if 'Votre identification est incorrecte' in message:
                    raise BrowserIncorrectPassword()
                assert False, 'Unhandled Server Error encountered: %s' % error.get('message', '')

        # accounts_url may contain '/particulier', '/professionnel' or '/association'
        self.accounts_url = self.page.get_accounts_url()
        assert self.accounts_url, 'Could not get accounts url from security check'
        self.location(self.accounts_url)
        assert self.accounts_page.is_here(), 'We failed to login after the security check!'
        # Once the security check is passed, we are logged in.

    @need_login
    def get_accounts_list(self):
        # Determine how many spaces are present on the connection:
        self.location(self.accounts_url)
        total_spaces = self.page.count_spaces()
        self.logger.info('The total number of spaces on this connection is %s.' % total_spaces)

        for contract in range(total_spaces):
            # This request often returns a 500 error so we retry several times.
            try:
                self.contracts_page.go(id_contract=contract)
            except ServerError:
                self.logger.warning('Server returned error 500 when trying to access space %s, we try again' % contract)
                try:
                    self.contracts_page.go(id_contract=contract)
                except ServerError:
                    self.logger.warning('Server returned error 500 twice when trying to access space %s, this space will be skipped' % contract)
                    continue

            # The main account is not located at the same place in the JSON.
            main_account = self.page.get_main_account()
            main_account.owner_type = self.page.get_owner_type()
            main_account._contract = contract

            accounts_list = list(self.page.iter_accounts())
            for account in accounts_list:
                account._contract = contract
                account.owner_type = self.page.get_owner_type()

            # Some accounts have no balance in the main JSON, so we must
            # get all the (id, balance) pairs in the account_details JSON:
            categories = {int(account._category) for account in accounts_list if account._category != None}
            account_balances = {}
            loan_ids = {}
            for category in categories:
                self.account_details.go(category=category)
                account_balances.update(self.page.get_account_balances())
                loan_ids.update(self.page.get_loan_ids())

            # Getting IBANs for checking accounts
            if main_account.type == Account.TYPE_CHECKING:
                params = {
                    'compteIdx': int(main_account._index),
                    'grandeFamilleCode': 1,
                }
                self.account_iban.go(params=params)
                iban = self.page.get_iban()
                if is_iban_valid(iban):
                    main_account.iban = iban
            yield main_account

            for card in main_account._cards:
                card.parent = main_account
                card.currency = main_account.currency
                card.owner_type = main_account.owner_type
                card._contract = contract
                yield card

            for account in accounts_list:
                if empty(account.balance):
                    account.balance = account_balances.get(account.id, NotAvailable)
                if account.type == Account.TYPE_CHECKING:
                    try:
                        params = {
                            'compteIdx': int(account._index),
                            'grandeFamilleCode': 1,
                        }
                        self.account_iban.go(params=params)
                        iban = self.page.get_iban()
                        if is_iban_valid(iban):
                            account.iban = iban
                    except ServerError:
                        self.logger.warning('Could not fetch IBAN for checking account "%s %s"', account.label, account.id)
                        pass

                # TO-DO: Create Loan() object with its related attributes
                # Loans have a specific ID that we need to fetch
                # so the backend can match loans properly.
                # If no there is no loan ID, we keep the account ID.
                if account.type == Account.TYPE_LOAN:
                    account.id = loan_ids.get(account.id, account.id)
                    account.balance = -account.balance
                elif account.type == Account.TYPE_REVOLVING_CREDIT:
                    account.id = loan_ids.get(account.id, account.id)
                    account.balance = 0
                yield account

    @need_login
    def go_to_account_space(self, contract):
        # TO-DO: Figure out a way to determine whether
        # we already are on the right account space
        self.contracts_page.go(id_contract=contract)
        assert self.accounts_page.is_here()

    @need_login
    def get_card(self, id):
        return find_object(self.get_cards(), id=id)

    @need_login
    def get_cards(self, accounts_list=None):
        # accounts_list is only used by get_list
        raise BrowserUnavailable()

    @need_login
    def get_history(self, account):
        raise BrowserUnavailable()

    @need_login
    def iter_investment(self, account):
        raise BrowserUnavailable()

    @need_login
    def iter_advisor(self):
        raise BrowserUnavailable()

    @need_login
    def get_profile(self):
        #self.profile.go()
        raise BrowserUnavailable()

    @need_login
    def iter_transfer_recipients(self, account):
        raise BrowserUnavailable()

    @need_login
    def init_transfer(self, transfer, **params):
        raise BrowserUnavailable()

    @need_login
    def execute_transfer(self, transfer, **params):
        raise BrowserUnavailable()

    @need_login
    def build_recipient(self, recipient):
        raise BrowserUnavailable()

    @need_login
    def new_recipient(self, recipient, **params):
        raise BrowserUnavailable()
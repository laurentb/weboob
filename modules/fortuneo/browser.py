# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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
from weboob.exceptions import AuthMethodNotImplemented, BrowserIncorrectPassword
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages.login import LoginPage, UnavailablePage
from .pages.accounts_list import (
    AccountsList, AccountHistoryPage, CardHistoryPage, InvestmentHistoryPage, PeaHistoryPage, LoanPage,
)
from .pages.transfer import (
    RegisterTransferPage, ValidateTransferPage, ConfirmTransferPage, RecipientsPage,
)

__all__ = ['Fortuneo']


class Fortuneo(LoginBrowser):
    BASEURL = 'https://mabanque.fortuneo.fr'

    login_page = URL(r'.*identification\.jsp.*', LoginPage)

    accounts_page = URL(r'/fr/prive/default.jsp\?ANav=1',
                        r'.*prive/default\.jsp.*',
                        r'.*/prive/mes-comptes/synthese-mes-comptes\.jsp',
                        AccountsList)
    account_history = URL(r'.*/prive/mes-comptes/livret/consulter-situation/consulter-solde\.jsp.*',
                          r'.*/prive/mes-comptes/compte-courant/consulter-situation/consulter-solde\.jsp.*',
                          r'.*/prive/mes-comptes/compte-especes.*',
                          AccountHistoryPage)
    card_history = URL(r'.*/prive/mes-comptes/compte-courant/carte-bancaire/encours-debit-differe\.jsp.*', CardHistoryPage)
    pea_history = URL(r'.*/prive/mes-comptes/pea/.*',
                      r'.*/prive/mes-comptes/compte-titres-pea/.*',
                      r'.*/prive/mes-comptes/ppe/.*', PeaHistoryPage)
    invest_history = URL(r'.*/prive/mes-comptes/assurance-vie/.*', InvestmentHistoryPage)
    loan_contract = URL(r'/fr/prive/mes-comptes/credit-immo/contrat-credit-immo/contrat-pret-immobilier.jsp.*', LoanPage)
    unavailable = URL(r'/customError/indispo.html', UnavailablePage)

    # transfer
    recipients = URL(
        r'/fr/prive/mes-comptes/compte-courant/realiser-operations/gerer-comptes-externes/consulter-comptes-externes.jsp',
        RecipientsPage)
    register_transfer = URL(
        r'/fr/prive/mes-comptes/compte-courant/realiser-operations/saisie-virement.jsp\?ca=(?P<ca>)',
        RegisterTransferPage)
    validate_transfer = URL(
        r'/fr/prive/mes-comptes/compte-courant/.*/verifier-saisie-virement.jsp',
        ValidateTransferPage)
    confirm_transfer = URL(
        r'fr/prive/mes-comptes/compte-courant/.*/init-confirmer-saisie-virement.jsp',
        r'/fr/prive/mes-comptes/compte-courant/.*/confirmer-saisie-virement.jsp',
        ConfirmTransferPage)

    def __init__(self, *args, **kwargs):
        LoginBrowser.__init__(self, *args, **kwargs)
        self.investments = {}
        self.action_needed_processed = False

    def do_login(self):
        if not self.login_page.is_here():
            self.location('/fr/identification.jsp')

        self.page.login(self.username, self.password)

        if self.login_page.is_here():
            raise BrowserIncorrectPassword()

        self.location('/fr/prive/default.jsp?ANav=1')
        if self.accounts_page.is_here() and self.page.need_sms():
            raise AuthMethodNotImplemented('Authentification with sms is not supported')

    @need_login
    def get_investments(self, account):
        if hasattr(account, '_investment_link'):
            if account.id in self.investments:
                return self.investments[account.id]
            else:
                self.location(account._investment_link)
                return self.page.get_investments(account)
        return []

    @need_login
    def get_history(self, account):
        self.location(account._history_link)
        if not account.type == Account.TYPE_LOAN:
            if self.page.select_period():
                return sorted_transactions(self.page.get_operations())

        return []

    @need_login
    def get_coming(self, account):
        for cb_link in account._card_links:
            for _ in range(3):
                self.location(cb_link)
                if not self.page.is_loading():
                    break
                time.sleep(1)

            for tr in sorted_transactions(self.page.get_operations()):
                yield tr

    @need_login
    def get_accounts_list(self):
        self.accounts_page.go()

        if not self.action_needed_processed:
            self.process_action_needed()

        assert self.accounts_page.is_here()
        return self.page.get_list()

    def process_action_needed(self):
        # we have to go in an iframe to know if there are CGUs
        url = self.page.get_iframe_url()
        if url:
            self.location(self.absurl(url, base=True)) # beware, the landing page might vary according to the referer page. So far I didn't figure out how the landing page is chosen.

            # if there are skippable CGUs, skip them
            if self.accounts_page.is_here() and self.page.has_action_needed():
                # Look for the request in the event listener registered to the button
                # can be harcoded, no variable part. It is a POST request without data.
                self.location(self.absurl('ReloadContext?action=1&', base=True), method='POST')
            self.accounts_page.go()  # go back to the accounts page whenever there was an iframe or not

        self.action_needed_processed = True

    @need_login
    def iter_recipients(self, origin_account):
        self.register_transfer.go(ca=origin_account._ca)
        if self.page.is_account_transferable(origin_account):
            for internal_recipient in self.page.iter_internal_recipients(origin_account_id=origin_account.id):
                yield internal_recipient

            self.recipients.go()
            for external_recipients in self.page.iter_external_recipients():
                yield external_recipients

    @need_login
    def init_transfer(self, account, recipient, amount, label, exec_date):
        self.register_transfer.go(ca=account._ca)
        self.page.fill_transfer_form(account, recipient, amount, label, exec_date)
        return self.page.handle_response(account, recipient, amount, label, exec_date)

    @need_login
    def execute_transfer(self, transfer):
        self.page.validate_transfer()
        self.page.confirm_transfer()
        return self.page.transfer_confirmation(transfer)

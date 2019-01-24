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

from __future__ import unicode_literals

import time
import json
from datetime import datetime, timedelta

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import AuthMethodNotImplemented, BrowserIncorrectPassword, ActionNeeded
from weboob.capabilities.bank import Account, AddRecipientStep, Recipient
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.value import Value

from .pages.login import LoginPage, UnavailablePage
from .pages.accounts_list import (
    AccountsList, AccountHistoryPage, CardHistoryPage, InvestmentHistoryPage, PeaHistoryPage, LoanPage, ProfilePage, ProfilePageCSV, SecurityPage, FakeActionPage,
)
from .pages.transfer import (
    RegisterTransferPage, ValidateTransferPage, ConfirmTransferPage, RecipientsPage, RecipientSMSPage
)

__all__ = ['Fortuneo']


class Fortuneo(LoginBrowser, StatesMixin):
    BASEURL = 'https://mabanque.fortuneo.fr'
    STATE_DURATION = 5

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
    security_page = URL(r'/fr/prive/identification-carte-securite-forte.jsp.*', SecurityPage)

    # transfer
    recipients = URL(
        r'/fr/prive/mes-comptes/compte-courant/realiser-operations/gerer-comptes-externes/consulter-comptes-externes.jsp',
        r'/fr/prive/verifier-compte-externe.jsp',
        r'fr/prive/mes-comptes/compte-courant/.*/gestion-comptes-externes.jsp',
        RecipientsPage)
    recipient_sms = URL(
        r'/fr/prive/appel-securite-forte-otp-bankone.jsp',
        r'/fr/prive/mes-comptes/compte-courant/.*/confirmer-ajout-compte-externe.jsp',
        RecipientSMSPage)
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
    fake_action_page = URL(r'fr/prive/mes-comptes/synthese-globale/synthese-mes-comptes.jsp', FakeActionPage)
    profile = URL(r'/fr/prive/informations-client.jsp', ProfilePage)
    profile_csv = URL(r'/PdfStruts\?*', ProfilePageCSV)

    need_reload_state = None

    __states__ = ['need_reload_state', 'add_recipient_form']

    def __init__(self, *args, **kwargs):
        LoginBrowser.__init__(self, *args, **kwargs)
        self.investments = {}
        self.action_needed_processed = False
        self.add_recipient_form = None

    def do_login(self):
        if not self.login_page.is_here():
            self.location('/fr/identification.jsp')

        self.page.login(self.username, self.password)

        if self.login_page.is_here():
            raise BrowserIncorrectPassword()

        self.location('/fr/prive/default.jsp?ANav=1')
        if self.accounts_page.is_here() and self.page.need_sms():
            raise AuthMethodNotImplemented('Authentification with sms is not supported')

    def load_state(self, state):
        # reload state only for new recipient feature
        if state.get('need_reload_state'):
            # don't use locate browser for add recipient step
            state.pop('url', None)
            super(Fortuneo, self).load_state(state)

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

        # Note: if you want to debug process_action_needed() here,
        # you must first set self.action_needed_processed to False
        # otherwise it might not enter the "if" loop here below.
        if not self.action_needed_processed:
            self.process_action_needed()

        assert self.accounts_page.is_here()
        accounts_list = self.page.get_list()
        if self.fake_action_page.is_here():
            # A false action needed is present, it's a choice to make Fortuno your main bank.
            # To avoid it, we need to first detect it on the account_page
            # Then make a post request to mimic the click on choice 'later'
            # And to finish we must to reload the page with a POST to get the accounts
            # before going on the accounts_page, which will have the data.
            self.location(self.absurl('ReloadContext?action=1&', base=True), method='POST')
            self.accounts_page.go()
            accounts_list = self.page.get_list()
        return accounts_list

    def process_action_needed(self):
        # we have to go in an iframe to know if there are CGUs
        url = self.page.get_iframe_url()
        if url:
            self.location(self.absurl(url, base=True)) # beware, the landing page might vary according to the referer page. So far I didn't figure out how the landing page is chosen.

            if self.security_page.is_here():
                # Some connections require reinforced security and we cannot bypass the OTP in order
                # to get to the account information. Users have to provide a phone number in order to
                # validate an OTP, so we must raise an ActionNeeded with the appropriate message.
                raise ActionNeeded('Cette opération sensible doit être validée par un code sécurité envoyé par SMS ou serveur vocal. '
                                   'Veuillez contacter le Service Clients pour renseigner vos coordonnées téléphoniques.')

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

    def copy_recipient(self, recipient):
        rcpt = Recipient()
        rcpt.iban = recipient.iban
        rcpt.id = recipient.iban
        rcpt.label = recipient.label
        rcpt.category = recipient.category
        rcpt.enabled_at = datetime.now().replace(microsecond=0) + timedelta(days=1)
        rcpt.currency = u'EUR'
        return rcpt

    def new_recipient(self, recipient, **params):
        if 'code' in params:
            # to drop and use self.add_recipient_form instead in send_code()
            recipient_form = json.loads(self.add_recipient_form)
            self.send_code(recipient_form ,params['code'])
            if self.page.rcpt_after_sms():
                self.need_reload_state = None
                return self.copy_recipient(recipient)
            elif self.page.is_code_expired():
                self.need_reload_state = True
                raise AddRecipientStep(recipient, Value('code', label='Le code sécurité est expiré. Veuillez saisir le nouveau code reçu qui sera valable 5 minutes.'))
            assert False, self.page.get_error()
        return self.new_recipient_before_otp(recipient, **params)

    @need_login
    def new_recipient_before_otp(self, recipient, **params):
        self.recipients.go()
        self.page.check_external_iban_form(recipient)
        self.page.check_recipient_iban()

        # fill form
        self.page.fill_recipient_form(recipient)
        rcpt = self.page.get_new_recipient(recipient)

        # get first part of confirm form
        send_code_form = self.page.get_send_code_form()

        data = {
            'appelAjax': 'true',
            'domicileUpdated': 'false',
            'numeroSelectionne.value': '',
            'portableUpdated': 'false',
            'proUpdated': 'false',
            'typeOperationSensible': 'AJOUT_BENEFICIAIRE'
        }
        # this send sms to user
        self.location(self.absurl('/fr/prive/appel-securite-forte-otp-bankone.jsp', base=True) , data=data)
        # get second part of confirm form
        send_code_form.update(self.page.get_send_code_form_input())

        # save form value and url for statesmixin
        self.add_recipient_form = dict(send_code_form)
        self.add_recipient_form.update({'url': send_code_form.url})

        # storage can't handle dict with '.' in key
        # to drop when dict with '.' in key is handled
        self.add_recipient_form = json.dumps(self.add_recipient_form)

        self.need_reload_state = True
        raise AddRecipientStep(rcpt, Value('code', label='Veuillez saisir le code reçu.'))

    def send_code(self, form_data, code):
        form_url = form_data['url']
        form_data['otp'] = code
        form_data.pop('url')
        self.location(self.absurl(form_url, base=True), data=form_data)

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

    @need_login
    def get_profile(self):
        self.profile.go()
        csv_link = self.page.get_csv_link()
        if csv_link:
            self.location(csv_link)
        return self.page.get_profile()

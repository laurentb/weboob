# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded
from weboob.capabilities.bank import Account, TransferBankError
from weboob.capabilities.base import find_object, NotAvailable
from weboob.browser.exceptions import BrowserHTTPNotFound
from weboob.capabilities.profile import ProfileMissing
from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .pages.accounts_list import (
    AccountsList, AccountHistory, CardsList, LifeInsurance,
    LifeInsuranceHistory, LifeInsuranceInvest, LifeInsuranceInvest2, Market, UnavailableServicePage,
    ListRibPage, AdvisorPage, HTMLProfilePage, XMLProfilePage, LoansPage, IbanPage, ComingPage,
)
from .pages.transfer import RecipientsPage, TransferPage, AddRecipientPage, RecipientJson
from .pages.login import LoginPage, BadLoginPage, ReinitPasswordPage, ActionNeededPage, ErrorPage
from .pages.subscription import BankStatementPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(LoginBrowser, StatesMixin):
    BASEURL = 'https://particuliers.secure.societegenerale.fr'
    STATE_DURATION = 5

    login = URL('https://particuliers.societegenerale.fr/index.html', LoginPage)
    action_needed = URL('/com/icd-web/forms/cct-index.html',
                        '/com/icd-web/gdpr/gdpr-recueil-consentements.html',
                        ActionNeededPage)
    bad_login = URL('\/acces/authlgn.html', '/error403.html', BadLoginPage)
    reinit = URL('/acces/changecodeobligatoire.html', ReinitPasswordPage)
    iban_page = URL(r'/lgn/url\.html\?dup', IbanPage)
    accounts = URL('/restitution/cns_listeprestation.html', AccountsList)
    coming_page = URL('/restitution/cns_listeEncours.xml', ComingPage)
    cards_list = URL('/restitution/cns_listeCartes.*.html', CardsList)
    account_history = URL('/restitution/cns_detail.*\.html', '/lgn/url.html', AccountHistory)
    market = URL('/brs/cct/comti20.html', Market)
    life_insurance = URL('/asv/asvcns10.html', '/asv/AVI/asvcns10a.html', '/brs/fisc/fisca10a.html', LifeInsurance)
    life_insurance_invest = URL('/asv/AVI/asvcns20a.html', LifeInsuranceInvest)
    life_insurance_invest_2 = URL('/asv/PRV/asvcns10priv.html', LifeInsuranceInvest2)
    life_insurance_history = URL('/asv/AVI/asvcns2(?P<n>[0-9])c.html', LifeInsuranceHistory)
    list_rib = URL('/restitution/imp_listeRib.html', ListRibPage)
    advisor = URL('/com/contacts.html', AdvisorPage)

    recipients = URL('/personnalisation/per_cptBen_modifier_liste.html', RecipientsPage)
    transfer = URL('/virement/pas_vipon_saisie.html', '/lgn/url.html', TransferPage)
    add_recipient = URL('/lgn/url.html', AddRecipientPage)
    json_recipient = URL('/sec/getsigninfo.json', '/sec/csa/send.json', '/sec/oob_sendoob.json', '/sec/oob_polling.json', RecipientJson)

    loans = URL(r'/abm/restit/listeRestitutionPretsNET.json\?a100_isPretConso=(?P<conso>\w+)', LoansPage)
    html_profile_page = URL(r'/com/dcr-web/dcr/dcr-coordonnees.html', HTMLProfilePage)
    xml_profile_page = URL(r'/gms/gmsRestituerAdresseNotificationServlet.xml', XMLProfilePage)
    unavailable_service_page = URL(r'/com/service-indisponible.html', UnavailableServicePage)

    bank_statement = URL(r'/restitution/rce_derniers_releves.html', BankStatementPage)
    bank_statement_search = URL(r'/restitution/rce_recherche.html\?noRedirect=1',
                                r'/restitution/rce_recherche_resultat.html', BankStatementPage)

    error = URL('https://static.societegenerale.fr/pri/erreur.html', ErrorPage)

    accounts_list = None
    context = None
    dup = None
    id_transaction = None

    __states__ = ('context', 'dup', 'id_transaction')

    def load_state(self, state):
        if state.get('dup') is not None and state.get('context') is not None:
            super(SocieteGenerale, self).load_state(state)

    def do_login(self):
        if not self.password.isdigit() or len(self.password) != 6:
            raise BrowserIncorrectPassword()
        if not self.username.isdigit() or len(self.username) < 8:
            raise BrowserIncorrectPassword()
        self.username = self.username[:8]

        self.login.stay_or_go()

        try:
            self.page.login(self.username, self.password)
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

        if self.login.is_here():
            raise BrowserIncorrectPassword()

        if self.bad_login.is_here():
            error = self.page.get_error()
            if error is None:
                raise BrowserIncorrectPassword()
            elif error.startswith('Votre session a'):
                raise BrowserUnavailable('Session has expired')
            elif error.startswith('Le service est momentan'):
                raise BrowserUnavailable(error)
            elif 'niv_auth_insuff' in error:
                raise BrowserIncorrectPassword("Niveau d'authentification insuffisant")
            elif 'Veuillez contacter' in error:
                raise ActionNeeded(error)
            else:
                raise BrowserIncorrectPassword(error)

    @need_login
    def get_accounts_list(self):
        if self.accounts_list is None:
            self.accounts.stay_or_go()
            self.accounts_list = self.page.get_list()
            # Coming amount is on another page, whose url must be retrieved on the main page
            self.location(self.page.get_coming_url())
            self.page.set_coming(self.accounts_list)
            self.list_rib.go()
            if self.list_rib.is_here():
                # Caching rib url, so we don't have to go back and forth for each account
                for account in self.accounts_list:
                    account._rib_url = self.page.get_rib_url(account)
                for account in self.accounts_list:
                    if account.type is Account.TYPE_MARKET:
                        self.location(account._link_id)
                        if isinstance(self.page, Market):
                            account.balance = self.page.get_balance(account.type) or account.balance
                    if account._rib_url:
                        self.location(account._rib_url)
                        if self.iban_page.is_here():
                            account.iban = self.page.get_iban()

            for type_ in ['true', 'false']:
                self.loans.go(conso=type_)
                # some loans page are unavailable
                if self.page.doc['commun']['statut'] == 'nok':
                    continue
                self.accounts_list.extend(self.page.iter_accounts())

        return iter(self.accounts_list)

    @need_login
    def iter_history(self, account):
        if not account._link_id:
            return
        self.location(account._link_id)

        if self.cards_list.is_here():
            for card_link in self.page.iter_cards():
                self.location(card_link)
                for trans in self.page.iter_transactions():
                    yield trans
        elif self.account_history.is_here():
            for trans in self.page.iter_transactions():
                yield trans

        elif self.life_insurance.is_here():
            for n in ('0', '1'):
                for i in range(3, -1, -1):
                    self.life_insurance_history.go(n=n)
                    if not self.page.get_error():
                        break
                    self.logger.warning('Life insurance error (%s), retrying %d more times', self.page.get_error(), i)
                else:
                    self.logger.warning('Life insurance error (%s), failed', self.page.get_error())
                    return

                for trans in self.page.iter_transactions():
                    yield trans

                # go to next page
                while self.page.doc.xpath('//div[@class="net2g_asv_tableau_pager"]/a[contains(@href, "actionSuivPage")]'):
                    form = self.page.get_form('//form[@id="operationForm"]')
                    form['a100_asv_action'] = 'actionSuivPage'
                    form.submit()
                    for trans in self.page.iter_transactions():
                        yield trans

        else:
            self.logger.warning('This account is not supported')

    @need_login
    def iter_investment(self, account):
        if account.type == Account.TYPE_MARKET:
            self.location(account._link_id)

        elif account.type == Account.TYPE_LIFE_INSURANCE:
            # Life Insurance type whose investments require scraping at '/asv/PRV/asvcns10priv.html':
            self.location(account._link_id)
            if self.page.has_link():
                # Other Life Insurance pages:
                self.life_insurance_invest.go()

        elif account.type == Account.TYPE_PEA:
            # Scraping liquidities for "PEA Espèces" accounts
            self.location(account._link_id)
            valuation = self.page.get_liquidities()
            if valuation != NotAvailable:
                yield create_french_liquidity(valuation)
            return

        else:
            self.logger.warning('This account is not supported')
            return

        for invest in self.page.iter_investment():
            yield invest

    @need_login
    def get_advisor(self):
        return self.advisor.stay_or_go().get_advisor()

    @need_login
    def iter_recipients(self, account):
        try:
            self.transfer.go()
        except TransferBankError:
            return
        if not self.page.is_able_to_transfer(account):
            return
        for recipient in self.page.iter_recipients(account_id=account.id):
            yield recipient
        # some connections have a lot of recipients but they only can do transfer to their own accounts
        if not self.page.has_external_recipient_transferable():
            return
        for recipient in self.recipients.go().iter_recipients():
            yield recipient

    @need_login
    def init_transfer(self, account, recipient, transfer):
        self.transfer.go().init_transfer(account, recipient, transfer)
        self.page.check_data_consistency(transfer)
        return self.page.create_transfer(account, recipient, transfer)

    @need_login
    def execute_transfer(self, transfer):
        self.page.confirm()
        return transfer

    def end_sms_recipient(self, recipient, **params):
        data = [('context', self.context), ('context', self.context), ('dup', self.dup), ('code', params['code']), ('csa_op', 'sign')]
        self.add_recipient.go(data=data, headers={'Referer': 'https://particuliers.secure.societegenerale.fr/lgn/url.html'})
        return self.page.get_recipient_object(recipient)

    def end_oob_recipient(self, recipient, **params):
        r = self.open('https://particuliers.secure.societegenerale.fr/sec/oob_polling.json', data={'n10_id_transaction': self.id_transaction})
        assert r.page.doc['donnees']['transaction_status'] in ('available', 'in_progress'), \
            'transaction_status is %s' % r.page.doc['donnees']['transaction_status']

        data = [('context', self.context), ('b64_jeton_transaction', self.context),
            ('dup', self.dup), ('n10_id_transaction', self.id_transaction), ('oob_op', 'sign')]
        self.add_recipient.go(data=data, headers={'Referer': 'https://particuliers.secure.societegenerale.fr/lgn/url.html'})
        return self.page.get_recipient_object(recipient)

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            return self.end_sms_recipient(recipient, **params)
        if 'pass' in params:
            return self.end_oob_recipient(recipient, **params)
        self.transfer.go()
        self.location(self.page.get_add_recipient_link())
        self.page.post_iban(recipient)
        self.page.post_label(recipient)
        self.page.double_auth(recipient)

    @need_login
    def get_profile(self):
        self.html_profile_page.go()
        profile = self.page.get_profile()
        self.xml_profile_page.go()
        profile.email = self.page.get_email()
        return profile

    @need_login
    def iter_subscription(self):
        try:
            profile = self.get_profile()
            subscriber = profile.name
        except ProfileMissing:
            subscriber = NotAvailable

        # subscriptions which have statements are present on the last statement page
        self.bank_statement.go()
        subscriptions_list = list(self.page.iter_subscription())

        # this way the no statement accounts are excluded
        # and the one keeped have all the data and parameters needed
        self.bank_statement_search.go()
        for sub in self.page.iter_searchable_subscription(subscriber=subscriber):
            found_sub = find_object(subscriptions_list, id=sub.id)
            if found_sub:
                yield sub

    @need_login
    def iter_documents(self, subscribtion):
        end_date = datetime.today()

        # 5 years since it goes with a 2 months step
        security_limit = 30
        i = 0
        while i < security_limit:
            self.bank_statement_search.go()
            self.page.post_form(subscribtion, end_date)

            # No more documents
            if self.page.has_error_msg():
                break

            for d in self.page.iter_documents(subscribtion):
                yield d

            # 3 months step because the documents list is inclusive
            # from the 08 to the 06, the 06 statement is included
            end_date = end_date - relativedelta(months=+3)
            i += 1

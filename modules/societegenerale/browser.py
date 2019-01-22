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
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.capabilities.bank import Account, TransferBankError
from weboob.capabilities.base import find_object, NotAvailable
from weboob.browser.exceptions import BrowserHTTPNotFound
from weboob.capabilities.profile import ProfileMissing

from .pages.accounts_list import (
    AccountsMainPage, AccountDetailsPage, AccountsPage, LoansPage, HistoryPage,
    CardHistoryPage, PeaLiquidityPage, AccountsSynthesesPage,
    AdvisorPage, HTMLProfilePage, XMLProfilePage, CreditPage, CreditHistoryPage,
    MarketPage, LifeInsurance, LifeInsuranceHistory, LifeInsuranceInvest, LifeInsuranceInvest2,
    UnavailableServicePage,
)
from .pages.transfer import AddRecipientPage, RecipientJson, TransferJson, SignTransferPage
from .pages.login import MainPage, LoginPage, BadLoginPage, ReinitPasswordPage, ActionNeededPage, ErrorPage
from .pages.subscription import BankStatementPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(LoginBrowser, StatesMixin):
    BASEURL = 'https://particuliers.societegenerale.fr'
    STATE_DURATION = 5

    # Bank
    accounts_main_page = URL(r'/restitution/cns_listeprestation.html',
                             r'/com/icd-web/cbo/index.html', AccountsMainPage)
    account_details_page = URL(r'/restitution/cns_detailPrestation.html', AccountDetailsPage)
    accounts = URL(r'/icd/cbo/data/liste-prestations-navigation-authsec.json', AccountsPage)
    accounts_syntheses = URL(r'/icd/cbo/data/liste-prestations-authsec.json\?n10_avecMontant=1', AccountsSynthesesPage)
    history = URL(r'/icd/cbo/data/liste-operations-authsec.json', HistoryPage)
    card_history = URL(r'/restitution/cns_listeReleveCarteDd.xml', CardHistoryPage)
    loans = URL(r'/abm/restit/listeRestitutionPretsNET.json\?a100_isPretConso=(?P<conso>\w+)', LoansPage)
    credit = URL(r'/restitution/cns_detailAVPAT.html', CreditPage)
    credit_history = URL(r'/restitution/cns_listeEcrCav.xml', CreditHistoryPage)

    # Recipient
    add_recipient = URL(r'/personnalisation/per_cptBen_ajouterFrBic.html',
                        r'/lgn/url.html', AddRecipientPage)
    json_recipient = URL(r'/sec/getsigninfo.json',
                         r'/sec/csa/send.json',
                         r'/sec/oob_sendoob.json',
                         r'/sec/oob_polling.json', RecipientJson)
    # Transfer
    json_transfer = URL(r'/icd/vupri/data/vupri-liste-comptes.json\?an200_isBack=false',
                        r'/icd/vupri/data/vupri-check.json',
                        r'/lgn/url.html', TransferJson)
    sign_transfer = URL(r'/icd/vupri/data/vupri-generate-token.json', SignTransferPage)
    confirm_transfer = URL(r'/icd/vupri/data/vupri-save.json', TransferJson)

    # Wealth
    market = URL(r'/brs/cct/comti20.html', MarketPage)
    pea_liquidity = URL(r'/restitution/cns_detailPea.html', PeaLiquidityPage)
    life_insurance = URL(r'/asv/asvcns10.html',
                         r'/asv/AVI/asvcns10a.html',
                         r'/brs/fisc/fisca10a.html', LifeInsurance)
    life_insurance_invest = URL(r'/asv/AVI/asvcns20a.html', LifeInsuranceInvest)
    life_insurance_invest_2 = URL(r'/asv/PRV/asvcns10priv.html', LifeInsuranceInvest2)
    life_insurance_history = URL(r'/asv/AVI/asvcns2(?P<n>[0-9])c.html', LifeInsuranceHistory)

    # Profile
    advisor = URL(r'/icd/pon/data/get-contacts.xml', AdvisorPage)
    html_profile_page = URL(r'/com/dcr-web/dcr/dcr-coordonnees.html', HTMLProfilePage)
    xml_profile_page = URL(r'/gms/gmsRestituerAdresseNotificationServlet.xml', XMLProfilePage)

    # Document
    bank_statement = URL(r'/restitution/rce_derniers_releves.html', BankStatementPage)
    bank_statement_search = URL(r'/restitution/rce_recherche.html\?noRedirect=1',
                                r'/restitution/rce_recherche_resultat.html', BankStatementPage)

    bad_login = URL(r'/acces/authlgn.html', r'/error403.html', BadLoginPage)
    reinit = URL(r'/acces/changecodeobligatoire.html',
                 r'/swm/swm-changemdpobligatoire.html', ReinitPasswordPage)
    action_needed = URL(r'/com/icd-web/forms/cct-index.html',
                        r'/com/icd-web/gdpr/gdpr-recueil-consentements.html',
                        r'/com/icd-web/forms/kyc-index.html',
                        ActionNeededPage)
    unavailable_service_page = URL(r'/com/service-indisponible.html',
                                   r'/Technical-pages/503-error-page/unavailable.html', UnavailableServicePage)
    error = URL(r'https://static.societegenerale.fr/pri/erreur.html', ErrorPage)
    login = URL(r'/sec/vk', LoginPage)
    main_page = URL(r'https://particuliers.societegenerale.fr', MainPage)

    context = None
    dup = None
    id_transaction = None

    __states__ = ('context', 'dup', 'id_transaction')

    def load_state(self, state):
        if state.get('dup') is not None and state.get('context') is not None:
            super(SocieteGenerale, self).load_state(state)

    def do_login(self):
        if not self.password.isdigit() or len(self.password) not in (6, 7):
            raise BrowserIncorrectPassword()
        if not self.username.isdigit() or len(self.username) < 8:
            raise BrowserIncorrectPassword()
        self.username = self.username[:8]

        self.main_page.go()
        try:
            self.page.login(self.username, self.password)
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

        assert self.login.is_here()
        reason, action = self.page.get_error()
        if reason == 'echec_authent':
            raise BrowserIncorrectPassword()
        if reason == 'acces_bloq':
            raise ActionNeeded()

    def iter_cards(self, account):
        for el in account._cards:
            if el['carteDebitDiffere']:
                card = Account()
                card.id = card.number = el['numeroCompteFormate'].replace(' ', '')
                card.label = el['labelToDisplay']
                card.coming = Decimal(str(el['montantProchaineEcheance']))
                card.type = Account.TYPE_CARD
                card.currency = account.currency
                card._internal_id = el['idTechnique']
                card._prestation_id = el['id']
                yield card

    @need_login
    def get_accounts_list(self):
        self.accounts_main_page.go()

        if self.page.is_old_website():
            # go on new_website
            self.location(self.absurl('/com/icd-web/cbo/index.html'))

        # get account iban on transfer page
        account_ibans = {}
        try:
            self.json_transfer.go()
        except TransferBankError:
            # some user can't access this page
            pass
        else:
            account_ibans = self.page.get_account_ibans_dict()

        # get accounts coming
        self.accounts_syntheses.go()
        account_comings = self.page.get_account_comings()

        self.accounts.go()
        for account in self.page.iter_accounts():
            for card in self.iter_cards(account):
                card.parent = account
                yield card

            if account._prestation_id in account_ibans:
                account.iban = account_ibans[account._prestation_id]

            if account._prestation_id in account_comings:
                account.coming = account_comings[account._prestation_id]

            if account.type == account.TYPE_LOAN:
                self.loans.go(conso=(account._loan_type == 'PR_CONSO'))
                account = self.page.get_loan_account(account)

            yield account

    @need_login
    def iter_history(self, account):
        if account.type in (account.TYPE_LOAN, account.TYPE_MARKET, ):
            return

        if account.type == Account.TYPE_PEA and not ('Espèces' in account.label or 'ESPECE' in account.label):
            return

        if account.type == account.TYPE_LIFE_INSURANCE:
            # request to get json is not available yet, old request to get html response
            self.account_details_page.go(params={'idprest': account._prestation_id})
            link = self.page.get_history_link()
            if link:
                self.location(self.absurl(link))
                for tr in self.page.iter_li_history():
                    yield tr
            return

        if account.type == account.TYPE_REVOLVING_CREDIT:
            # request to get json is not available yet, old request to get html response
            self.account_details_page.go(params={'idprest': account._prestation_id})
            self.page.go_history_page()
            for tr in self.page.iter_credit_history():
                yield tr
            return

        if account.type == account.TYPE_CARD:
            self.history.go(params={'b64e200_prestationIdTechnique': account.parent._internal_id})
            for summary_card_tr in self.page.iter_card_transactions(card_number=account.number):
                yield summary_card_tr

                for card_tr in summary_card_tr._card_transactions:
                    card_tr.date = summary_card_tr.date
                    yield card_tr
            return

        self.history.go(params={'b64e200_prestationIdTechnique': account._internal_id})
        for transaction in self.page.iter_history():
            yield transaction

    @need_login
    def iter_coming(self, account):
        if account.type in (account.TYPE_LOAN, account.TYPE_MARKET, account.TYPE_PEA,
                            account.TYPE_LIFE_INSURANCE, account.TYPE_REVOLVING_CREDIT):
            return

        internal_id = account._internal_id
        if account.type == account.TYPE_CARD:
            internal_id = account.parent._internal_id
        self.history.go(params={'b64e200_prestationIdTechnique': internal_id})

        if account.type == account.TYPE_CARD:
            for transaction in self.page.iter_future_transactions(acc_prestation_id=account._prestation_id):
                # coming transactions on this page are not in coming balance
                # except for defered card coming transaction, use only for it for the moment
                if transaction._card_coming:
                    for card_coming in transaction._card_coming:
                        card_coming.date = transaction.date
                        yield card_coming
                    return

        for intraday_tr in self.page.iter_intraday_comings():
            yield intraday_tr

    @need_login
    def iter_investment(self, account):
        if account.type not in (Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE, Account.TYPE_PEA):
            self.logger.debug('This account is not supported')
            return

        # request to get json is not available yet, old request to get html response
        self.account_details_page.go(params={'idprest': account._prestation_id})

        if account.type in (Account.TYPE_PEA, Account.TYPE_MARKET):
            for invest in self.page.iter_investments(account=account):
                yield invest

        if account.type == Account.TYPE_LIFE_INSURANCE:
            if self.page.has_link():
                self.life_insurance_invest.go()

            for invest in self.page.iter_investment():
                yield invest

    @need_login
    def iter_recipients(self, account):
        try:
            self.json_transfer.go()
        except TransferBankError:
            return []
        if not self.page.is_able_to_transfer(account):
            return []
        return self.page.iter_recipients(account_id=account.id)

    @need_login
    def init_transfer(self, account, recipient, transfer):
        self.json_transfer.go()

        first_transfer_date = self.page.get_first_available_transfer_date()
        if transfer.exec_date and transfer.exec_date < first_transfer_date:
            transfer.exec_date = first_transfer_date

        self.page.init_transfer(account, recipient, transfer)
        return self.page.handle_response(recipient)

    @need_login
    def execute_transfer(self, transfer):
        assert transfer.id, 'Transfer token is missing'
        data = {
            'b64e200_idVirement': transfer.id
        }
        # get token and virtual keyboard
        self.sign_transfer.go(params=data)

        data.update(self.page.get_confirm_transfer_data(self.password))
        # execute transfer
        headers = {'Referer': self.absurl('/com/icd-web/vupri/virement.html')}
        self.confirm_transfer.go(data=data, headers=headers)

        assert self.page.is_transfer_validated(), 'Something went wrong, transfer is not executed'
        return transfer

    def end_sms_recipient(self, recipient, **params):
        data = [('context', self.context), ('context', self.context), ('dup', self.dup), ('code', params['code']), ('csa_op', 'sign')]
        self.add_recipient.go(data=data, headers={'Referer': self.absurl('/lgn/url.html')})
        return self.page.get_recipient_object(recipient)

    def end_oob_recipient(self, recipient, **params):
        r = self.open(self.absurl('/sec/oob_polling.json'), data={'n10_id_transaction': self.id_transaction})
        assert r.page.doc['donnees']['transaction_status'] in ('available', 'in_progress'), \
            'transaction_status is %s' % r.page.doc['donnees']['transaction_status']

        if r.page.doc['donnees']['transaction_status'] == 'in_progress':
            raise ActionNeeded('Veuillez valider le bénéficiaire sur votre application bancaire.')

        data = [
            ('context', self.context),
            ('b64_jeton_transaction', self.context),
            ('dup', self.dup),
            ('n10_id_transaction', self.id_transaction),
            ('oob_op', 'sign')
        ]
        add_recipient_url = self.absurl('/lgn/url.html', base=True)
        self.location(
            add_recipient_url,
            data=data,
            headers={'Referer': add_recipient_url}
        )
        return self.page.get_recipient_object(recipient)

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            return self.end_sms_recipient(recipient, **params)
        if 'pass' in params:
            return self.end_oob_recipient(recipient, **params)
        self.add_recipient.go()
        self.page.post_iban(recipient)
        self.page.post_label(recipient)
        self.page.double_auth(recipient)

    @need_login
    def get_advisor(self):
        return self.advisor.go().get_advisor()

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

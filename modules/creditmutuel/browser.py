# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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

import re
import time
from datetime import datetime
from itertools import groupby
from operator import attrgetter

from weboob.exceptions import (
    ActionNeeded, AppValidation, AppValidationExpired, AppValidationCancelled, AuthMethodNotImplemented,
    BrowserIncorrectPassword, BrowserUnavailable, BrowserQuestion, NoAccountsException,
)
from weboob.tools.compat import basestring
from weboob.tools.value import Value
from weboob.tools.capabilities.bank.transactions import FrenchTransaction, sorted_transactions
from weboob.browser.browsers import need_login, TwoFactorBrowser
from weboob.browser.profiles import Wget
from weboob.browser.url import URL
from weboob.browser.pages import FormNotFound
from weboob.browser.exceptions import ClientError, ServerError
from weboob.capabilities.bank import Account, AddRecipientStep, Recipient, AccountOwnership
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.capabilities import NotAvailable
from weboob.tools.compat import urlparse
from weboob.capabilities.base import find_object, empty

from .pages import (
    LoginPage, LoginErrorPage, AccountsPage, UserSpacePage,
    OperationsPage, CardPage, ComingPage, RecipientsListPage,
    ChangePasswordPage, VerifCodePage, EmptyPage, PorPage,
    IbanPage, NewHomePage, AdvisorPage, RedirectPage,
    LIAccountsPage, CardsActivityPage, CardsListPage,
    CardsOpePage, NewAccountsPage, InternalTransferPage,
    ExternalTransferPage, RevolvingLoanDetails, RevolvingLoansList,
    ErrorPage, SubscriptionPage, NewCardsListPage, CardPage2, FiscalityConfirmationPage,
    ConditionsPage, MobileConfirmationPage, UselessPage, DecoupledStatePage, CancelDecoupled,
    OtpValidationPage, OtpBlockedErrorPage, TwoFAUnabledPage,
    LoansOperationsPage,
)


__all__ = ['CreditMutuelBrowser']


class CreditMutuelBrowser(TwoFactorBrowser):
    PROFILE = Wget()
    TIMEOUT = 30
    BASEURL = 'https://www.creditmutuel.fr'
    HAS_CREDENTIALS_ONLY = True
    STATE_DURATION = 5
    TWOFA_DURATION = 60 * 24 * 90

    # connexion
    login = URL(
        r'/fr/authentification.html',
        r'/(?P<subbank>.*)fr/$',
        r'/(?P<subbank>.*)fr/banques/accueil.html',
        r'/(?P<subbank>.*)fr/banques/particuliers/index.html',
        LoginPage
    )
    login_error = URL(r'/(?P<subbank>.*)fr/identification/default.cgi',      LoginErrorPage)
    twofa_unabled_page = URL(r'/(?P<subbank>.*)fr/banque/validation.aspx', TwoFAUnabledPage)
    mobile_confirmation = URL(r'/(?P<subbank>.*)fr/banque/validation.aspx', MobileConfirmationPage)
    decoupled_state = URL(r'/fr/banque/async/otp/SOSD_OTP_GetTransactionState.htm', DecoupledStatePage)
    cancel_decoupled = URL(r'/fr/banque/async/otp/SOSD_OTP_CancelTransaction.htm', CancelDecoupled)
    otp_validation_page = URL(r'/(?P<subbank>.*)fr/banque/validation.aspx', OtpValidationPage)
    otp_blocked_error_page = URL(r'/(?P<subbank>.*)fr/banque/validation.aspx', OtpBlockedErrorPage)
    fiscality = URL(r'/(?P<subbank>.*)fr/banque/residencefiscale.aspx', FiscalityConfirmationPage)

    # accounts
    accounts =    URL(r'/(?P<subbank>.*)fr/banque/situation_financiere.cgi',
                      r'/(?P<subbank>.*)fr/banque/situation_financiere.html',
                      AccountsPage)
    useless_page = URL(r'/(?P<subbank>.*)fr/banque/paci/defi-solidaire.html', UselessPage)

    revolving_loan_list = URL(r'/(?P<subbank>.*)fr/banque/CR/arrivee.asp\?fam=CR.*', RevolvingLoansList)
    revolving_loan_details = URL(r'/(?P<subbank>.*)fr/banque/CR/cam9_vis_lstcpt.asp.*', RevolvingLoanDetails)
    user_space =  URL(r'/(?P<subbank>.*)fr/banque/espace_personnel.aspx',
                      r'/(?P<subbank>.*)fr/banque/accueil.cgi',
                      r'/(?P<subbank>.*)fr/banque/DELG_Gestion',
                      r'/(?P<subbank>.*)fr/banque/paci_engine/engine.aspx',
                      r'/(?P<subbank>.*)fr/banque/paci_engine/static_content_manager.aspx',
                      UserSpacePage)
    card =        URL(r'/(?P<subbank>.*)fr/banque/operations_carte.cgi.*',
                      r'/(?P<subbank>.*)fr/banque/mouvements.html\?webid=.*cardmonth=\d+$',
                      r'/(?P<subbank>.*)fr/banque/mouvements.html.*webid=.*cardmonth=\d+.*cardid=',
                      CardPage)
    operations =  URL(r'/(?P<subbank>.*)fr/banque/mouvements.cgi.*',
                      r'/(?P<subbank>.*)fr/banque/mouvements.html.*',
                      r'/(?P<subbank>.*)fr/banque/nr/nr_devbooster.aspx.*',
                      r'(?P<subbank>.*)fr/banque/CRP8_GESTPMONT.aspx\?webid=.*&trnref=.*&contract=\d+&cardid=.*&cardmonth=\d+',
                      OperationsPage)
    # This loans_operations contains operation for some loans, but not all of them.
    loans_operations = URL(r'/(?P<subbank>.*)fr/banque/gec9.aspx.*', LoansOperationsPage)
    coming =      URL(r'/(?P<subbank>.*)fr/banque/mvts_instance.cgi.*',      ComingPage)
    info =        URL(r'/(?P<subbank>.*)fr/banque/BAD.*',                    EmptyPage)
    change_pass = URL(r'/(?P<subbank>.*)fr/validation/change_password.cgi',
                      '/fr/services/change_password.html', ChangePasswordPage)
    verify_pass = URL(r'/(?P<subbank>.*)fr/validation/verif_code.cgi.*',
                      r'/(?P<subbank>.*)fr/validation/lst_codes.cgi.*', VerifCodePage)
    new_home =    URL(r'/(?P<subbank>.*)fr/banque/pageaccueil.html',
                      r'/(?P<subbank>.*)banque/welcome_pack.html', NewHomePage)
    empty =       URL(r'/(?P<subbank>.*)fr/banques/index.html',
                      r'/(?P<subbank>.*)fr/banque/paci_beware_of_phishing.*',
                      r'/(?P<subbank>.*)fr/validation/(?!change_password|verif_code|image_case|infos).*',
                      EmptyPage)
    por =         URL(r'/(?P<subbank>.*)fr/banque/POR_ValoToute.aspx',
                      r'/(?P<subbank>.*)fr/banque/POR_SyntheseLst.aspx',
                      PorPage)
    por_action_needed = URL(r'/(?P<subbank>.*)fr/banque/ORDR_InfosGenerales.aspx', EmptyPage)

    li =          URL(r'/(?P<subbank>.*)fr/assurances/profilass.aspx\?domaine=epargne',
                      r'/(?P<subbank>.*)fr/assurances/(consultations?/)?WI_ASS.*',
                      r'/(?P<subbank>.*)fr/assurances/WI_ASS',
                      '/fr/assurances/', LIAccountsPage)
    iban =        URL(r'/(?P<subbank>.*)fr/banque/rib.cgi', IbanPage)

    new_accounts = URL(r'/(?P<subbank>.*)fr/banque/comptes-et-contrats.html', NewAccountsPage)
    new_operations = URL(r'/(?P<subbank>.*)fr/banque/mouvements.cgi',
                         r'/fr/banque/nr/nr_devbooster.aspx.*',
                         r'/(?P<subbank>.*)fr/banque/RE/aiguille(liste)?.asp',
                         '/fr/banque/mouvements.html',
                         r'/(?P<subbank>.*)fr/banque/consultation/operations', OperationsPage)

    advisor = URL(r'/(?P<subbank>.*)fr/banques/contact/trouver-une-agence/(?P<page>.*)',
                  r'/(?P<subbank>.*)fr/infoclient/',
                  r'/(?P<subbank>.*)fr/banques/accueil/menu-droite/Details.aspx\?banque=.*',
                  AdvisorPage)

    redirect = URL(r'/(?P<subbank>.*)fr/banque/paci_engine/static_content_manager.aspx', RedirectPage)

    cards_activity = URL(r'/(?P<subbank>.*)fr/banque/pro/ENC_liste_tiers.aspx', CardsActivityPage)
    cards_list = URL(r'/(?P<subbank>.*)fr/banque/pro/ENC_liste_ctr.*',
                     r'/(?P<subbank>.*)fr/banque/pro/ENC_detail_ctr', CardsListPage)
    cards_ope = URL(r'/(?P<subbank>.*)fr/banque/pro/ENC_liste_oper', CardsOpePage)
    cards_ope2 = URL('/(?P<subbank>.*)fr/banque/CRP8_SCIM_DEPCAR.aspx', CardPage2)

    cards_hist_available = URL('/(?P<subbank>.*)fr/banque/SCIM_default.aspx\?_tabi=C&_stack=SCIM_ListeActivityStep%3a%3a&_pid=ListeCartes&_fid=ChangeList&Data_ServiceListDatas_CurrentType=MyCards',
                               '/(?P<subbank>.*)fr/banque/PCS1_CARDFUNCTIONS.aspx', NewCardsListPage)
    cards_hist_available2 = URL('/(?P<subbank>.*)fr/banque/SCIM_default.aspx', NewCardsListPage)

    internal_transfer = URL(r'/(?P<subbank>.*)fr/banque/virements/vplw_vi.html', InternalTransferPage)
    external_transfer = URL(r'/(?P<subbank>.*)fr/banque/virements/vplw_vee.html', ExternalTransferPage)
    recipients_list =   URL(r'/(?P<subbank>.*)fr/banque/virements/vplw_bl.html', RecipientsListPage)
    error = URL(r'/(?P<subbank>.*)validation/infos.cgi', ErrorPage)

    subscription = URL(r'/(?P<subbank>.*)fr/banque/MMU2_LstDoc.aspx', SubscriptionPage)
    terms_and_conditions = URL(r'/(?P<subbank>.*)fr/banque/conditions-generales.html',
                               r'/(?P<subbank>.*)fr/banque/coordonnees_personnelles.aspx',
                               r'/(?P<subbank>.*)fr/banque/paci_engine/paci_wsd_pdta.aspx',
                               r'/(?P<subbank>.*)fr/banque/reglementation-dsp2.html', ConditionsPage)

    currentSubBank = None
    is_new_website = None
    form = None
    logged = None
    need_clear_storage = None
    accounts_list = None

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.weboob = kwargs['weboob']
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(CreditMutuelBrowser, self).__init__(config, *args, **kwargs)

        self.__states__ += (
            'currentSubBank', 'form', 'logged', 'is_new_website',
            'need_clear_storage', 'recipient_form',
            'twofa_auth_state', 'polling_data', 'otp_data',
        )
        self.twofa_auth_state = {}
        self.polling_data = {}
        self.otp_data = {}
        self.keep_session = None
        self.recipient_form = None

        self.AUTHENTICATION_METHODS = {
            'resume': self.handle_polling,
            'code': self.handle_sms,
        }

    def get_expire(self):
        if self.twofa_auth_state:
            expires = datetime.fromtimestamp(self.twofa_auth_state['expires']).isoformat()
            return expires
        return

    def load_state(self, state):
        # when add recipient fails, state can't be reloaded.
        # If state is reloaded, there is this error message:
        # "Navigation interdite - Merci de bien vouloir recommencer votre action."
        if state.get('need_clear_storage'):
            # only keep 'twofa_auth_state' state to avoid new 2FA
            state = {'twofa_auth_state': state.get('twofa_auth_state')}

        if state.get('polling_data') or state.get('recipient_form') or state.get('otp_data'):
            # can't start on an url in the middle of a validation process
            # or server will cancel it and launch another one
            if 'url' in state:
                state.pop('url')

        # if state is empty (first login), it does nothing
        super(CreditMutuelBrowser, self).load_state(state)

    def finalize_twofa(self, twofa_data):
        """
        Go to validated 2FA url. Before following redirection,
        store 'auth_client_state' cookie to prove to server,
        for a TWOFA_DURATION, that 2FA is already done.
        """

        self.location(
            twofa_data['final_url'],
            data=twofa_data['final_url_params'],
            allow_redirects=False
        )

        for cookie in self.session.cookies:
            if cookie.name == 'auth_client_state':
                # only present if 2FA is valid
                self.twofa_auth_state['value'] = cookie.value  # this is a token
                self.twofa_auth_state['expires'] = cookie.expires  # this is a timestamp
                self.location(self.response.headers['Location'])

    def handle_polling(self):
        # 15' on website, we don't wait that much, but leave sufficient time for the user
        timeout = time.time() + 600.00  # 15' on webview, need not to wait that much

        while time.time() < timeout:
            data = {'transactionId': self.polling_data['polling_id']}
            self.decoupled_state.go(data=data)

            decoupled_state = self.page.get_decoupled_state()
            if decoupled_state == 'VALIDATED':
                self.logger.info('AppValidation done, going to final_url')
                self.finalize_twofa(self.polling_data)
                self.polling_data = {}
                return
            elif decoupled_state in ('CANCELLED', 'NONE'):
                self.polling_data = {}
                raise AppValidationCancelled()

            assert decoupled_state == 'PENDING', 'Unhandled polling state: "%s"' % decoupled_state
            time.sleep(5)  # every second on wbesite, need to slow that down

        # manually cancel polling before website max duration for it
        self.cancel_decoupled.go(data=data)
        self.polling_data = {}
        raise AppValidationExpired()

    def check_otp_blocked(self):
        # Too much wrong OTPs, locked down after total 3 wrong inputs
        if self.otp_blocked_error_page.is_here():
            error_msg = self.page.get_error_message()
            raise BrowserUnavailable(error_msg)

    def handle_sms(self):
        self.otp_data['final_url_params']['otp_password'] = self.code
        self.finalize_twofa(self.otp_data)

        ## cases where 2FA is not finalized
        # Too much wrong OTPs, locked down after total 3 wrong inputs
        self.check_otp_blocked()

        # OTP is expired after 15', we end up on login page
        if self.login.is_here():
            raise BrowserIncorrectPassword("Le code de confirmation envoyé par SMS n'est plus utilisable")

        # Wrong OTP leads to same form with error message, re-raise BrowserQuestion
        elif self.otp_validation_page.is_here():
            error_msg = self.page.get_error_message()
            if 'erroné' not in error_msg:
                raise BrowserUnavailable(error_msg)
            else:
                label = '%s %s' % (error_msg, self.page.get_message())
                raise BrowserQuestion(Value('code', label=label))

        self.otp_data = {}

    def check_redirections(self):
        self.logger.info('Checking redirections')
        # MobileConfirmationPage or OtpValidationPage is coming but there is no request_information
        location = self.response.headers.get('Location', '')
        if 'validation.aspx' in location and not self.is_interactive:
            self.check_interactive()
        elif location:
            self.location(location, allow_redirects=False)

    def check_auth_methods(self):
        if self.mobile_confirmation.is_here():
            self.page.check_bypass()
            if self.mobile_confirmation.is_here():
                self.polling_data = self.page.get_polling_data()
                assert self.polling_data, "Can't proceed to polling if no polling_data"
                raise AppValidation(self.page.get_validation_msg())

        if self.otp_validation_page.is_here():
            self.otp_data = self.page.get_otp_data()
            assert self.otp_data, "Can't proceed to SMS handling if no otp_data"
            raise BrowserQuestion(Value('code', label=self.page.get_message()))

        self.check_otp_blocked()

    def init_login(self):
        self.login.go()

        # 2FA already done, if valid, login() redirects to home page
        if self.twofa_auth_state:
            self.session.cookies.set('auth_client_state', self.twofa_auth_state['value'])
            self.page.login(self.username, self.password, redirect=True)

        if not self.page.logged:
            # 302 redirect to catch to know if polling
            self.page.login(self.username, self.password)
            self.check_redirections()
            # for cic, there is two redirections
            self.check_redirections()
            if self.twofa_unabled_page.is_here():
                raise ActionNeeded(self.page.get_error_msg())

            # when people try to log in but there are on a sub site of creditmutuel
            if not self.page and not self.url.startswith(self.BASEURL):
                raise BrowserIncorrectPassword()

            if self.login_error.is_here():
                raise BrowserIncorrectPassword()

        if self.verify_pass.is_here():
            raise AuthMethodNotImplemented("L'identification renforcée avec la carte n'est pas supportée.")

        self.check_auth_methods()

        self.getCurrentSubBank()

    def ownership_guesser(self):
        profile = self.get_profile()
        psu_names = profile.name.lower().split()

        for account in self.accounts_list:
            label = account.label.lower()
            # We try to find "M ou Mme" or "Mlle XXX ou M XXXX" for example (non-exhaustive exemple list)
            if re.search(r'.* ((m) ([\w].*|ou )?(m[ml]e)|(m[ml]e) ([\w].*|ou )(m) ).*', label):
                account.ownership = AccountOwnership.CO_OWNER

            # We check if the PSU firstname and lastname is in the account label
            elif all(name in label.split() for name in psu_names):
                account.ownership = AccountOwnership.OWNER

        # Card Accounts should be set with the same ownership of their parents
        for account in self.accounts_list:
            if account.type == Account.TYPE_CARD and not empty(account.parent):
                account.ownership = account.parent.ownership


    @need_login
    def get_accounts_list(self):
        if not self.accounts_list:
            if self.currentSubBank is None:
                self.getCurrentSubBank()

            self.two_cards_page = None
            self.accounts_list = []
            self.revolving_accounts = []
            self.unavailablecards = []
            self.cards_histo_available = []
            self.cards_list =[]
            self.cards_list2 =[]

            # For some cards the validity information is only availaible on these 2 links
            self.cards_hist_available.go(subbank=self.currentSubBank)
            if self.cards_hist_available.is_here():
                self.unavailablecards.extend(self.page.get_unavailable_cards())
                for acc in self.page.iter_accounts():
                    acc._referer = self.cards_hist_available
                    self.accounts_list.append(acc)
                    self.cards_list.append(acc)
                    self.cards_histo_available.append(acc.id)

            if not self.cards_list:
                self.cards_hist_available2.go(subbank=self.currentSubBank)
                if self.cards_hist_available2.is_here():
                    self.unavailablecards.extend(self.page.get_unavailable_cards())
                    for acc in self.page.iter_accounts():
                        acc._referer = self.cards_hist_available2
                        self.accounts_list.append(acc)
                        self.cards_list.append(acc)
                        self.cards_histo_available.append(acc.id)

            for acc in self.revolving_loan_list.stay_or_go(subbank=self.currentSubBank).iter_accounts():
                self.accounts_list.append(acc)
                self.revolving_accounts.append(acc.label.lower())

            # Handle cards on tiers page
            self.cards_activity.go(subbank=self.currentSubBank)
            companies = self.page.companies_link() if self.cards_activity.is_here() else \
                        [self.page] if self.is_new_website else []
            for company in companies:
                # We need to return to the main page to avoid navigation error
                self.cards_activity.go(subbank=self.currentSubBank)
                page = self.open(company).page if isinstance(company, basestring) else company
                for card in page.iter_cards():
                    card2 = find_object(self.cards_list, id=card.id[:16])
                    if card2:
                        # In order to keep the id of the card from the old space, we exchange the following values
                        card._link_id = card2._link_id
                        card._parent_id = card2._parent_id
                        card.coming = card2.coming
                        card._referer = card2._referer
                        card._secondpage = card2._secondpage
                        self.accounts_list.remove(card2)
                    self.accounts_list.append(card)
                    self.cards_list2.append(card)
            self.cards_list.extend(self.cards_list2)

            # Populate accounts from old website
            if not self.is_new_website:
                self.logger.info('On old creditmutuel website')
                self.accounts.stay_or_go(subbank=self.currentSubBank)
                has_no_account = self.page.has_no_account()
                self.accounts_list.extend(self.page.iter_accounts())
                self.iban.go(subbank=self.currentSubBank).fill_iban(self.accounts_list)
                self.por.go(subbank=self.currentSubBank)
                self.page.add_por_accounts(self.accounts_list)
            # Populate accounts from new website
            else:
                self.new_accounts.stay_or_go(subbank=self.currentSubBank)
                has_no_account = self.page.has_no_account()
                self.accounts_list.extend(self.page.iter_accounts())
                self.iban.go(subbank=self.currentSubBank).fill_iban(self.accounts_list)
                self.por.go(subbank=self.currentSubBank)
                self.page.add_por_accounts(self.accounts_list)

            self.li.go(subbank=self.currentSubBank)
            self.accounts_list.extend(self.page.iter_li_accounts())

            # This type of account is like a loan, for splitting payments in smaller amounts.
            # Its history is irrelevant because money is debited from a checking account and
            # the balance is not even correct, so ignore it.
            excluded_label = ['etalis', 'valorisation totale']

            accounts_by_id = {}
            for acc in self.accounts_list:
                if acc.label.lower() not in excluded_label:
                    accounts_by_id[acc.id] = acc

            # Set the parent to loans and cards accounts
            for acc in self.accounts_list:
                if acc.type == Account.TYPE_CARD and not empty(getattr(acc, '_parent_id', None)):
                    acc.parent = accounts_by_id.get(acc._parent_id, NotAvailable)

                elif acc.type in (Account.TYPE_MORTGAGE, Account.TYPE_LOAN) and acc._parent_id:
                    acc.parent = accounts_by_id.get(acc._parent_id, NotAvailable)

            self.accounts_list = list(accounts_by_id.values())

            if has_no_account and not self.accounts_list:
                raise NoAccountsException(has_no_account)

        self.ownership_guesser()

        return self.accounts_list

    def get_account(self, _id):
        assert isinstance(_id, basestring)

        for a in self.get_accounts_list():
            if a.id == _id:
                return a

    def getCurrentSubBank(self):
        # the account list and history urls depend on the sub bank of the user
        paths = urlparse(self.url).path.lstrip('/').split('/')
        self.currentSubBank = paths[0] + "/" if paths[0] != "fr" else ""
        if self.currentSubBank and paths[0] == 'banqueprivee' and paths[1] == 'mabanque':
            self.currentSubBank = 'banqueprivee/mabanque/'
        if self.currentSubBank and paths[1] == "decouverte":
            self.currentSubBank += paths[1] + "/"
        if paths[0] in ["cmmabn", "fr", "mabanque", "banqueprivee"]:
            self.is_new_website = True

    def list_operations(self, page, account):
        if isinstance(page, basestring):
            if page.startswith('/') or page.startswith('https') or page.startswith('?'):
                self.location(page)
            else:
                try:
                    self.location('%s/%sfr/banque/%s' % (self.BASEURL, self.currentSubBank, page))
                except ServerError as e:
                    self.logger.warning('Page cannot be visited: %s/%sfr/banque/%s: %s', self.BASEURL, self.currentSubBank, page, e)
                    raise BrowserUnavailable()
        else:
            self.page = page

        # On some savings accounts, the page lands on the contract tab, and we want the situation
        if account.type == Account.TYPE_SAVINGS and "Capital Expansion" in account.label:
            self.page.go_on_history_tab()

        if self.li.is_here():
            return self.page.iter_history()

        if self.is_new_website and self.page:
            try:
                for page in range(1, 50):
                    # Need to reach the page with all transactions
                    if not self.page.has_more_operations():
                        break
                    form = self.page.get_form(id="I1:P:F")
                    form['_FID_DoLoadMoreTransactions'] = ''
                    form['_wxf2_pseq'] = page
                    form.submit()
            # IndexError when form xpath returns [], StopIteration if next called on empty iterable
            except (StopIteration, FormNotFound):
                self.logger.warning('Could not get history on new website')
            except IndexError:
                # 6 months history is not available
                pass

        while self.page:
            try:
                # Submit form if their is more transactions to fetch
                form = self.page.get_form(id="I1:fm")
                if self.page.doc.xpath('boolean(//a[@class="ei_loadmorebtn"])'):
                    form['_FID_DoLoadMoreTransactions'] = ""
                    form.submit()
                else:
                    break
            except (IndexError, FormNotFound):
                break
            # Sometimes the browser can't go further
            except ClientError as exc:
                if exc.response.status_code == 413:
                    break
                raise

        if not self.operations.is_here():
            return iter([])

        return self.pagination(lambda: self.page.get_history())

    def get_monthly_transactions(self, trs):
        date_getter = attrgetter('date')
        groups = [list(g) for k, g in groupby(sorted(trs, key=date_getter), date_getter)]
        trs = []
        for group in groups:
            if group[0].date > datetime.today().date():
                continue
            tr = FrenchTransaction()
            tr.raw = tr.label = "RELEVE CARTE %s" % group[0].date
            tr.amount = -sum(t.amount for t in group)
            tr.date = tr.rdate = tr.vdate = group[0].date
            tr.type = FrenchTransaction.TYPE_CARD_SUMMARY
            tr._is_coming = False
            tr._is_manualsum = True
            trs.append(tr)
        return trs

    @need_login
    def get_history(self, account):
        transactions = []
        if not account._link_id:
            raise NotImplementedError()

        if len(account.id) >= 16 and account.id[:16] in self.cards_histo_available:
            if self.two_cards_page:
                # In this case, you need to return to the page where the iter account get the cards information
                # Indeed, for the same position of card in the two pages the url, headers and parameters are exactly the same
                account._referer.go(subbank=self.currentSubBank)
                if account._secondpage:
                    self.location(self.page.get_second_page_link())
            # Check if '000000xxxxxx0000' card have an annual history
            self.location(account._link_id)
            # The history of the card is available for 1 year with 1 month per page
            # Here we catch all the url needed to be the more compatible with the catch of merged subtransactions
            urlstogo = self.page.get_links()
            self.location(account._link_id)
            half_history = 'firstHalf'
            for url in urlstogo:
                transactions = []
                self.location(url)
                if 'GoMonthPrecedent' in url:
                    # To reach the 6 last month of history you need to change this url parameter
                    # Moreover we are on a transition page where we see the 6 next month (no scrapping here)
                    half_history = 'secondHalf'
                else:
                    history = self.page.get_history()
                    self.tr_date = self.page.get_date()
                    amount_summary = self.page.get_amount_summary()
                    if self.page.has_more_operations():
                        for i in range(1, 100):
                            # Arbitrary range; it's the number of click needed to access to the full history of the month (stop with the next break)
                            data = {
                                '_FID_DoAddElem': '',
                                '_wxf2_cc':	'fr-FR',
                                '_wxf2_pmode':	'Normal',
                                '_wxf2_pseq':	i,
                                '_wxf2_ptarget':	'C:P:updPan',
                                'Data_ServiceListDatas_CurrentOtherCardThirdPartyNumber': '',
                                'Data_ServiceListDatas_CurrentType':	'MyCards',
                            }
                            if 'fid=GoMonth&mois=' in self.url:
                                m = re.search(r'fid=GoMonth&mois=(\d+)', self.url)
                                if m:
                                    m = m.group(1)
                                self.location('CRP8_SCIM_DEPCAR.aspx?_tabi=C&a__itaret=as=SCIM_ListeActivityStep\%3a\%3a\%2fSCIM_ListeRouter%3a%3a&a__mncret=SCIM_LST&a__ecpid=EID2011&_stack=_remote::moiSelectionner={},moiAfficher={},typeDepense=T&_pid=SCIM_DEPCAR_Details'.format(m, half_history), data=data)
                            else:
                                self.location(self.url, data=data)

                            if not self.page.has_more_operations_xml():
                                history = self.page.iter_history_xml(date=self.tr_date)
                                # We are now with an XML page with all the transactions of the month
                                break
                    else:
                        history = self.page.get_history(date=self.tr_date)

                    for tr in history:
                        # For regrouped transaction, we have to go through each one to get details
                        if tr._regroup:
                            self.location(tr._regroup)
                            for tr2 in self.page.get_tr_merged():
                                tr2._is_coming = tr._is_coming
                                tr2.date = self.tr_date
                                transactions.append(tr2)
                        else:
                            transactions.append(tr)

                    if transactions and self.tr_date < datetime.today().date():
                        tr = FrenchTransaction()
                        tr.raw = tr.label = "RELEVE CARTE %s" % self.tr_date
                        tr.amount = amount_summary
                        tr.date = tr.rdate = tr.vdate = self.tr_date
                        tr.type = FrenchTransaction.TYPE_CARD_SUMMARY
                        tr._is_coming = False
                        tr._is_manualsum = True
                        transactions.append(tr)

                    for tr in sorted_transactions(transactions):
                        yield tr

        else:
            # need to refresh the months select
            if account._link_id.startswith('ENC_liste_oper'):
                self.location(account._pre_link)

            if not hasattr(account, '_card_pages'):
                for tr in self.list_operations(account._link_id, account):
                    transactions.append(tr)

            coming_link = self.page.get_coming_link() if self.operations.is_here() else None
            if coming_link is not None:
                for tr in self.list_operations(coming_link, account):
                    transactions.append(tr)

            deferred_date = None
            cards = ([page.select_card(account._card_number) for page in account._card_pages]
                     if hasattr(account, '_card_pages')
                     else account._card_links if hasattr(account, '_card_links') else [])
            for card in cards:
                card_trs = []
                for tr in self.list_operations(card, account):
                    if tr._to_delete:
                        # Delete main transaction when subtransactions exist
                        continue
                    if hasattr(tr, '_deferred_date') and (not deferred_date or tr._deferred_date < deferred_date):
                        deferred_date = tr._deferred_date
                    if tr.date >= datetime.now():
                        tr._is_coming = True
                    elif hasattr(account, '_card_pages'):
                        card_trs.append(tr)
                    transactions.append(tr)
                if card_trs:
                    transactions.extend(self.get_monthly_transactions(card_trs))

            if deferred_date is not None:
                # set deleted for card_summary
                for tr in transactions:
                    tr.deleted = (tr.type == FrenchTransaction.TYPE_CARD_SUMMARY
                                  and deferred_date.month <= tr.date.month
                                  and not hasattr(tr, '_is_manualsum'))

            for tr in sorted_transactions(transactions):
                yield tr

    @need_login
    def get_investment(self, account):
        if account._is_inv:
            if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
                self.por.go(subbank=self.currentSubBank)
                self.page.send_form(account)
            elif account.type == Account.TYPE_LIFE_INSURANCE:
                if not account._link_inv:
                    return iter([])
                self.location(account._link_inv)
            return self.page.iter_investment()
        if account.type is Account.TYPE_PEA:
            liquidities = create_french_liquidity(account.balance)
            liquidities.label = account.label
            return [liquidities]
        return iter([])

    @need_login
    def iter_recipients(self, origin_account):
        # access the transfer page
        self.internal_transfer.go(subbank=self.currentSubBank)
        if self.page.can_transfer(origin_account.id):
            for recipient in self.page.iter_recipients(origin_account=origin_account):
                yield recipient
        self.external_transfer.go(subbank=self.currentSubBank)
        if self.page.can_transfer(origin_account.id):
            origin_account._external_recipients = set()
            if self.page.has_transfer_categories():
                for category in self.page.iter_categories():
                    self.page.go_on_category(category['index'])
                    self.page.IS_PRO_PAGE = True
                    for recipient in self.page.iter_recipients(origin_account=origin_account, category=category['name']):
                        yield recipient
            else:
                for recipient in self.page.iter_recipients(origin_account=origin_account):
                    yield recipient

    @need_login
    def init_transfer(self, account, to, amount, exec_date, reason=None):
        if to.category != 'Interne':
            self.external_transfer.go(subbank=self.currentSubBank)
        else:
            self.internal_transfer.go(subbank=self.currentSubBank)

        if self.external_transfer.is_here() and self.page.has_transfer_categories():
            for category in self.page.iter_categories():
                if category['name'] == to.category:
                    self.page.go_on_category(category['index'])
                    break
            self.page.IS_PRO_PAGE = True
            self.page.RECIPIENT_STRING = 'data_input_indiceBen'
        self.page.prepare_transfer(account, to, amount, reason, exec_date)
        return self.page.handle_response(account, to, amount, reason, exec_date)

    @need_login
    def execute_transfer(self, transfer, **params):
        form = self.page.get_form(id='P:F', submit='//input[@type="submit" and contains(@value, "Confirmer")]')
        # For the moment, don't ask the user if he confirms the duplicate.
        form['Bool:data_input_confirmationDoublon'] = 'true'
        form.submit()
        return self.page.create_transfer(transfer)

    @need_login
    def get_advisor(self):
        advisor = None
        if not self.is_new_website:
            self.logger.info('On old creditmutuel website')
            self.accounts.stay_or_go(subbank=self.currentSubBank)
            if self.page.get_advisor_link():
                advisor = self.page.get_advisor()
                self.location(self.page.get_advisor_link()).page.update_advisor(advisor)
        else:
            advisor = self.new_accounts.stay_or_go(subbank=self.currentSubBank).get_advisor()
            link = self.page.get_agency()
            if link:
                link = link.replace(':443/', '/')
                self.location(link)
                self.page.update_advisor(advisor)
        return iter([advisor]) if advisor else iter([])

    @need_login
    def get_profile(self):
        if not self.is_new_website:
            self.logger.info('On old creditmutuel website')
            profile = self.accounts.stay_or_go(subbank=self.currentSubBank).get_profile()
        else:
            profile = self.new_accounts.stay_or_go(subbank=self.currentSubBank).get_profile()
        return profile

    def get_recipient_object(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = recipient.iban
        r.label = recipient.label
        r.category = recipient.category
        # On credit mutuel recipients are immediatly available.
        r.enabled_at = datetime.now().replace(microsecond=0)
        r.currency = 'EUR'
        r.bank_name = NotAvailable
        return r

    def format_recipient_form(self, key):
        self.recipient_form['[t:xsd%3astring;]Data_KeyInput'] = key

        # we don't know the card id
        # by default all users have only one card
        # but to be sure, let's get it dynamically
        do_validate = [k for k in self.recipient_form.keys() if '_FID_DoValidate_cardId' in k]
        assert len(do_validate) == 1, 'There should be only one card.'
        self.recipient_form[do_validate[0]] = ''

        activate = [k for k in self.recipient_form.keys() if '_FID_GoCardAction_action' in k]
        for _ in activate:
            del self.recipient_form[_]

    def continue_new_recipient(self, recipient, **params):
        if 'Clé' in params:
            url = self.recipient_form.pop('url')
            self.format_recipient_form(params['Clé'])
            self.location(url, data=self.recipient_form)
            self.recipient_form = None
            if self.verify_pass.is_here():
                self.page.handle_error()
                assert False, 'An error occured while checking the card code'
        self.page.add_recipient(recipient)
        if self.page.bic_needed():
            self.page.ask_bic(self.get_recipient_object(recipient))
        self.page.ask_sms(self.get_recipient_object(recipient))

    def send_sms(self, sms):
        data = {}
        for k, v in self.form.items():
            if k != 'url':
                data[k] = v
        data['otp_password'] = sms
        data['_FID_DoConfirm.x'] = '1'
        data['_FID_DoConfirm.y'] = '1'
        data['global_backup_hidden_key'] = ''
        self.location(self.form['url'], data=data)

    def end_new_recipient(self, recipient, **params):
        self.send_sms(params['code'])
        self.form = None
        self.page = None
        self.logged = 0
        return self.get_recipient_object(recipient)

    def post_with_bic(self, recipient, **params):
        data = {}
        for k, v in self.form.items():
            if k != 'url':
                data[k] = v
        data['[t:dbt%3astring;x(11)]data_input_BIC'] = params['Bic']
        self.location(self.form['url'], data=data)
        self.page.ask_sms(self.get_recipient_object(recipient))

    def set_new_recipient(self, recipient, **params):
        if self.currentSubBank is None:
            self.getCurrentSubBank()

        if 'Bic' in params:
            return self.post_with_bic(recipient, **params)
        if 'code' in params:
            return self.end_new_recipient(recipient, **params)
        if 'Clé' in params:
            return self.continue_new_recipient(recipient, **params)

        assert False, 'An error occured while adding a recipient.'

    @need_login
    def new_recipient(self, recipient, **params):
        if self.currentSubBank is None:
            self.getCurrentSubBank()

        self.recipients_list.go(subbank=self.currentSubBank)
        if self.page.has_list():
            assert recipient.category in self.page.get_recipients_list(), \
                'Recipient category "%s" is not on the website available list.' % recipient.category
            self.page.go_list(recipient.category)

        self.page.go_to_add()
        if self.verify_pass.is_here():
            self.page.check_personal_keys_error()
            self.recipient_form = self.page.get_recipient_form()
            raise AddRecipientStep(self.get_recipient_object(recipient), Value('Clé', label=self.page.get_question()))
        else:
            return self.continue_new_recipient(recipient, **params)

    @need_login
    def iter_subscriptions(self):
        if self.currentSubBank is None:
            self.getCurrentSubBank()
        self.subscription.go(subbank=self.currentSubBank)
        return self.page.iter_subscriptions()

    @need_login
    def iter_documents(self, subscription):
        if self.currentSubBank is None:
            self.getCurrentSubBank()
        self.subscription.go(subbank=self.currentSubBank, params={'typ': 'doc'})

        security_limit = 10

        for i in range(security_limit):
            for doc in self.page.iter_documents(sub_id=subscription.id):
                yield doc

            if self.page.is_last_page():
                break

            self.page.next_page()

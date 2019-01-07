# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from itertools import groupby
from operator import attrgetter

from weboob.tools.compat import basestring
from weboob.tools.value import Value
from weboob.tools.capabilities.bank.transactions import FrenchTransaction, sorted_transactions
from weboob.browser.browsers import LoginBrowser, need_login, StatesMixin
from weboob.browser.profiles import Wget
from weboob.browser.url import URL
from weboob.browser.pages import FormNotFound
from weboob.browser.exceptions import ClientError, ServerError
from weboob.exceptions import BrowserIncorrectPassword, AuthMethodNotImplemented, BrowserUnavailable
from weboob.capabilities.bank import Account, AddRecipientStep, Recipient
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.capabilities import NotAvailable
from weboob.tools.compat import urlparse
from weboob.capabilities.base import find_object

from .pages import (
    LoginPage, LoginErrorPage, AccountsPage, UserSpacePage,
    OperationsPage, CardPage, ComingPage, RecipientsListPage,
    ChangePasswordPage, VerifCodePage, EmptyPage, PorPage,
    IbanPage, NewHomePage, AdvisorPage, RedirectPage,
    LIAccountsPage, CardsActivityPage, CardsListPage,
    CardsOpePage, NewAccountsPage, InternalTransferPage,
    ExternalTransferPage, RevolvingLoanDetails, RevolvingLoansList,
    ErrorPage, SubscriptionPage, NewCardsListPage, CardPage2
)


__all__ = ['CreditMutuelBrowser']


class CreditMutuelBrowser(LoginBrowser, StatesMixin):
    PROFILE = Wget()
    STATE_DURATION = 10
    TIMEOUT = 30
    BASEURL = 'https://www.creditmutuel.fr'

    login =       URL('/fr/authentification.html',
                      r'/(?P<subbank>.*)fr/$',
                      r'/(?P<subbank>.*)fr/banques/accueil.html',
                      r'/(?P<subbank>.*)fr/banques/particuliers/index.html',
                      LoginPage)
    login_error = URL(r'/(?P<subbank>.*)fr/identification/default.cgi',      LoginErrorPage)
    accounts =    URL(r'/(?P<subbank>.*)fr/banque/situation_financiere.cgi',
                      r'/(?P<subbank>.*)fr/banque/situation_financiere.html',
                      AccountsPage)
    revolving_loan_list = URL(r'/(?P<subbank>.*)fr/banque/CR/arrivee.asp\?fam=CR.*', RevolvingLoansList)
    revolving_loan_details = URL(r'/(?P<subbank>.*)fr/banque/CR/cam9_vis_lstcpt.asp.*', RevolvingLoanDetails)
    user_space =  URL(r'/(?P<subbank>.*)fr/banque/espace_personnel.aspx',
                      r'/(?P<subbank>.*)fr/banque/accueil.cgi',
                      r'/(?P<subbank>.*)fr/banque/DELG_Gestion',
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

    cards_hist_available = URL('/(?P<subbank>.*)fr/banque/SCIM_default.aspx\?_tabi=C&_stack=SCIM_ListeActivityStep%3a%3a&_pid=ListeCartes&_fid=ChangeList&Data_ServiceListDatas_CurrentType=MyCards', NewCardsListPage)
    cards_hist_available2 = URL('/(?P<subbank>.*)fr/banque/SCIM_default.aspx', NewCardsListPage)

    internal_transfer = URL(r'/(?P<subbank>.*)fr/banque/virements/vplw_vi.html', InternalTransferPage)
    external_transfer = URL(r'/(?P<subbank>.*)fr/banque/virements/vplw_vee.html', ExternalTransferPage)
    recipients_list =   URL(r'/(?P<subbank>.*)fr/banque/virements/vplw_bl.html', RecipientsListPage)
    error = URL(r'/(?P<subbank>.*)validation/infos.cgi', ErrorPage)

    subscription = URL(r'/(?P<subbank>.*)fr/banque/MMU2_LstDoc.aspx', SubscriptionPage)

    currentSubBank = None
    is_new_website = None
    form = None
    logged = None
    need_clear_storage = None

    __states__ = ['currentSubBank', 'form', 'logged', 'is_new_website', 'need_clear_storage']

    accounts_list = None

    def load_state(self, state):
        # when add recipient fails, state can't be reloaded. If state is reloaded, there is this error message:
        # "Navigation interdite - Merci de bien vouloir recommencer votre action."
        if not state.get('need_clear_storage'):
            super(CreditMutuelBrowser, self).load_state(state)
        else:
            self.need_clear_storage = None

    def do_login(self):
        # Clear cookies.
        self.do_logout()

        self.login.go()

        if not self.page.logged:
            self.page.login(self.username, self.password)

            # when people try to log in but there are on a sub site of creditmutuel
            if not self.page and not self.url.startswith(self.BASEURL):
                raise BrowserIncorrectPassword()

            if not self.page.logged or self.login_error.is_here():
                raise BrowserIncorrectPassword()

        if self.verify_pass.is_here():
            raise AuthMethodNotImplemented("L'identification renforcée avec la carte n'est pas supportée.")

        self.getCurrentSubBank()

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
                self.accounts.stay_or_go(subbank=self.currentSubBank)
                self.accounts_list.extend(self.page.iter_accounts())
                self.iban.go(subbank=self.currentSubBank).fill_iban(self.accounts_list)
                self.por.go(subbank=self.currentSubBank).add_por_accounts(self.accounts_list)
            # Populate accounts from new website
            else:
                self.new_accounts.stay_or_go(subbank=self.currentSubBank)
                self.accounts_list.extend(self.page.iter_accounts())
                self.iban.go(subbank=self.currentSubBank).fill_iban(self.accounts_list)
                self.por.go(subbank=self.currentSubBank).add_por_accounts(self.accounts_list)

            self.li.go(subbank=self.currentSubBank)
            self.accounts_list.extend(self.page.iter_li_accounts())

            for acc in self.cards_list:
                if hasattr(acc, '_parent_id'):
                    acc.parent = find_object(self.accounts_list, id=acc._parent_id)

            excluded_label = ['etalis', 'valorisation totale']
            self.accounts_list = [acc for acc in self.accounts_list if not any(w in acc.label.lower() for w in excluded_label)]

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
        if paths[0] in ["fr", "mabanque"]:
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

        # Getting about 6 months history on new website
        if self.is_new_website and self.page:
            try:
                # Submit search form two times, at first empty, then filled based on available fields
                for x in range(2):
                    form = self.page.get_form(id="I1:fm", submit='//input[@name="_FID_DoActivateSearch"]')
                    if x == 1:
                        form.update({
                            next(k for k in form.keys() if "DateStart" in k): (datetime.now() - relativedelta(months=7)).strftime('%d/%m/%Y'),
                            next(k for k in form.keys() if "DateEnd" in k): datetime.now().strftime('%d/%m/%Y')
                        })
                        for k in form.keys():
                            if "_FID_Do" in k and "DoSearch" not in k:
                                form.pop(k, None)
                    form.submit()
            # IndexError when form xpath returns [], StopIteration if next called on empty iterable
            except (IndexError, StopIteration, FormNotFound):
                self.logger.warning('Could not get history on new website')

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

        if self.li.is_here():
            return self.page.iter_history()

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

            differed_date = None
            cards = ([page.select_card(account._card_number) for page in account._card_pages]
                     if hasattr(account, '_card_pages')
                     else account._card_links if hasattr(account, '_card_links') else [])
            for card in cards:
                card_trs = []
                for tr in self.list_operations(card, account):
                    if tr._to_delete:
                        # Delete main transaction when subtransactions exist
                        continue
                    if hasattr(tr, '_differed_date') and (not differed_date or tr._differed_date < differed_date):
                        differed_date = tr._differed_date
                    if tr.date >= datetime.now():
                        tr._is_coming = True
                    elif hasattr(account, '_card_pages'):
                        card_trs.append(tr)
                    transactions.append(tr)
                if card_trs:
                    transactions.extend(self.get_monthly_transactions(card_trs))

            if differed_date is not None:
                # set deleted for card_summary
                for tr in transactions:
                    tr.deleted = (tr.type == FrenchTransaction.TYPE_CARD_SUMMARY
                                  and differed_date.month <= tr.date.month
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

    def continue_new_recipient(self, recipient, **params):
        if 'Clé' in params:
            self.page.post_code(params['Clé'])
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

    @need_login
    def new_recipient(self, recipient, **params):
        if self.currentSubBank is None:
            self.getCurrentSubBank()
        if 'Bic' in params:
            return self.post_with_bic(recipient, **params)
        if 'code' in params:
            return self.end_new_recipient(recipient, **params)
        if 'Clé' in params:
            return self.continue_new_recipient(recipient, **params)

        self.recipients_list.go(subbank=self.currentSubBank)
        if self.page.has_list():
            assert recipient.category in self.page.get_recipients_list(), \
                'Recipient category is not on the website available list.'
            self.page.go_list(recipient.category)

        self.page.go_to_add()
        if self.verify_pass.is_here():
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

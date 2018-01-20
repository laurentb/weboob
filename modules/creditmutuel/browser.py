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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from itertools import groupby

from weboob.tools.compat import basestring
from weboob.tools.value import Value
from weboob.tools.capabilities.bank.transactions import FrenchTransaction, sorted_transactions
from weboob.browser.browsers import LoginBrowser, need_login, StatesMixin
from weboob.browser.profiles import Wget
from weboob.browser.url import URL
from weboob.browser.pages import FormNotFound
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword, AuthMethodNotImplemented
from weboob.capabilities.bank import Account, AddRecipientStep, AddRecipientError, Recipient
from weboob.capabilities import NotAvailable
from weboob.tools.compat import urlparse

from .pages import LoginPage, LoginErrorPage, AccountsPage, UserSpacePage, \
                   OperationsPage, CardPage, ComingPage, RecipientsListPage, \
                   ChangePasswordPage, VerifCodePage, EmptyPage, PorPage, \
                   IbanPage, NewHomePage, AdvisorPage, RedirectPage, \
                   LIAccountsPage, CardsActivityPage, CardsListPage,       \
                   CardsOpePage, NewAccountsPage, InternalTransferPage, \
                   ExternalTransferPage, RevolvingLoanDetails, RevolvingLoansList


__all__ = ['CreditMutuelBrowser']


class CreditMutuelBrowser(LoginBrowser, StatesMixin):
    PROFILE = Wget()
    STATE_DURATION = 15
    TIMEOUT = 30
    BASEURL = 'https://www.creditmutuel.fr'

    login =       URL('/fr/authentification.html',
                      '/(?P<subbank>.*)fr/$',
                      '/(?P<subbank>.*)fr/banques/accueil.html',
                      '/(?P<subbank>.*)fr/banques/particuliers/index.html',
                      LoginPage)
    login_error = URL('/(?P<subbank>.*)fr/identification/default.cgi',      LoginErrorPage)
    accounts =    URL('/(?P<subbank>.*)fr/banque/situation_financiere.cgi',
                      '/(?P<subbank>.*)fr/banque/situation_financiere.html',
                      AccountsPage)
    revolving_loan_list = URL(r'/(?P<subbank>.*)fr/banque/CR/arrivee.asp\?fam=CR.*', RevolvingLoansList)
    revolving_loan_details = URL(r'/(?P<subbank>.*)fr/banque/CR/cam9_vis_lstcpt.asp.*', RevolvingLoanDetails)
    user_space =  URL('/(?P<subbank>.*)fr/banque/espace_personnel.aspx',
                      '/(?P<subbank>.*)fr/banque/accueil.cgi',
                      '/(?P<subbank>.*)fr/banque/DELG_Gestion',
                      '/(?P<subbank>.*)fr/banque/paci_engine/static_content_manager.aspx',
                      UserSpacePage)
    card =        URL('/(?P<subbank>.*)fr/banque/operations_carte.cgi.*',
                      '/(?P<subbank>.*)fr/banque/mouvements.html\?webid=.*cardmonth=\d+$',
                      '/(?P<subbank>.*)fr/banque/mouvements.html.*webid=.*cardmonth=\d+.*cardid=',
                      CardPage)
    operations =  URL('/(?P<subbank>.*)fr/banque/mouvements.cgi.*',
                      '/(?P<subbank>.*)fr/banque/mouvements.html.*',
                      '/(?P<subbank>.*)fr/banque/nr/nr_devbooster.aspx.*',
                      r'(?P<subbank>.*)fr/banque/CRP8_GESTPMONT.aspx\?webid=.*&trnref=.*&contract=\d+&cardid=.*&cardmonth=\d+',
                      OperationsPage)
    coming =      URL('/(?P<subbank>.*)fr/banque/mvts_instance.cgi.*',      ComingPage)
    info =        URL('/(?P<subbank>.*)fr/banque/BAD.*',                    EmptyPage)
    change_pass = URL('/(?P<subbank>.*)fr/validation/change_password.cgi',
                      '/fr/services/change_password.html', ChangePasswordPage)
    verify_pass = URL('/(?P<subbank>.*)fr/validation/verif_code.cgi.*',     VerifCodePage)
    new_home =    URL('/(?P<subbank>.*)fr/banque/pageaccueil.html',
                      '/(?P<subbank>.*)banque/welcome_pack.html', NewHomePage)
    empty =       URL('/(?P<subbank>.*)fr/banques/index.html',
                      '/(?P<subbank>.*)fr/banque/paci_beware_of_phishing.*',
                      '/(?P<subbank>.*)fr/validation/(?!change_password|verif_code|image_case).*',
                      EmptyPage)
    por =         URL('/(?P<subbank>.*)fr/banque/POR_ValoToute.aspx',
                      '/(?P<subbank>.*)fr/banque/POR_SyntheseLst.aspx',
                      PorPage)
    li =          URL('/(?P<subbank>.*)fr/assurances/profilass.aspx\?domaine=epargne',
                      '/(?P<subbank>.*)fr/assurances/(consultations?/)?WI_ASS.*',
                      '/(?P<subbank>.*)fr/assurances/WI_ASS',
                      '/fr/assurances/', LIAccountsPage)
    iban =        URL('/(?P<subbank>.*)fr/banque/rib.cgi', IbanPage)

    new_accounts = URL('/(?P<subbank>.*)fr/banque/comptes-et-contrats.html', NewAccountsPage)
    new_operations = URL('/(?P<subbank>.*)fr/banque/mouvements.cgi',
                         '/fr/banque/nr/nr_devbooster.aspx.*',
                         '/(?P<subbank>.*)fr/banque/RE/aiguille(liste)?.asp',
                         '/fr/banque/mouvements.html',
                         '/(?P<subbank>.*)fr/banque/consultation/operations', OperationsPage)

    advisor = URL('/(?P<subbank>.*)fr/banques/contact/trouver-une-agence/(?P<page>.*)',
                  '/(?P<subbank>.*)fr/infoclient/',
                  r'/(?P<subbank>.*)fr/banques/accueil/menu-droite/Details.aspx\?banque=.*',
                  AdvisorPage)

    redirect = URL('/(?P<subbank>.*)fr/banque/paci_engine/static_content_manager.aspx', RedirectPage)

    cards_activity = URL('/(?P<subbank>.*)fr/banque/pro/ENC_liste_tiers.aspx', CardsActivityPage)
    cards_list = URL('/(?P<subbank>.*)fr/banque/pro/ENC_liste_ctr.*',
                     '/(?P<subbank>.*)fr/banque/pro/ENC_detail_ctr', CardsListPage)
    cards_ope = URL('/(?P<subbank>.*)fr/banque/pro/ENC_liste_oper', CardsOpePage)

    internal_transfer = URL('/(?P<subbank>.*)fr/banque/virements/vplw_vi.html', InternalTransferPage)
    external_transfer = URL('/(?P<subbank>.*)fr/banque/virements/vplw_vee.html', ExternalTransferPage)
    recipients_list =   URL('/(?P<subbank>.*)fr/banque/virements/vplw_bl.html', RecipientsListPage)

    currentSubBank = None
    is_new_website = False
    form = None
    logged = None

    __states__ = ['currentSubBank', 'form', 'logged']

    accounts_list = None

    def do_login(self):
        # Clear cookies.
        self.do_logout()

        self.login.go()

        if not self.page.logged:
            self.page.login(self.username, self.password)

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
            self.accounts_list = []

            # Handle cards on tiers page
            self.cards_activity.go(subbank=self.currentSubBank)
            companies = self.page.companies_link() if self.cards_activity.is_here() else \
                        [self.page] if self.is_new_website else []
            for company in companies:
                page = self.open(company).page if isinstance(company, basestring) else company
                self.accounts_list.extend([card for card in page.iter_cards()])

            if not self.is_new_website:
                for a in self.accounts.stay_or_go(subbank=self.currentSubBank).iter_accounts():
                    self.accounts_list.append(a)
                self.iban.go(subbank=self.currentSubBank).fill_iban(self.accounts_list)
                self.por.go(subbank=self.currentSubBank).add_por_accounts(self.accounts_list)
            else:
                for a in self.new_accounts.stay_or_go(subbank=self.currentSubBank).iter_accounts():
                    self.accounts_list.append(a)
                self.iban.go(subbank=self.currentSubBank).fill_iban(self.accounts_list)
                self.por.go(subbank=self.currentSubBank).add_por_accounts(self.accounts_list)

            for acc in self.li.go(subbank=self.currentSubBank).iter_li_accounts():
                self.accounts_list.append(acc)

            for acc in self.revolving_loan_list.stay_or_go(subbank=self.currentSubBank).iter_accounts():
                self.accounts_list.append(acc)

            excluded_label = ['etalis', 'valorisation totale']
            self.accounts_list = [acc for acc in self.accounts_list if not any(w in acc.label.lower() for w in excluded_label)]

        return self.accounts_list

    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list():
            if a.id == id:
                return a

    def getCurrentSubBank(self):
        # the account list and history urls depend on the sub bank of the user
        paths = urlparse(self.url).path.lstrip('/').split('/')
        self.currentSubBank = paths[0] + "/" if paths[0] != "fr" else ""
        if paths[0] in ["fr", "mabanque"]:
            self.is_new_website = True

    def list_operations(self, page, account):
        if isinstance(page, basestring):
            if page.startswith('/') or page.startswith('https') or page.startswith('?'):
                self.location(page)
            else:
                self.location('%s/%sfr/banque/%s' % (self.BASEURL, self.currentSubBank, page))
        else:
            self.page = page

        # on some savings accounts, the page lands on the contract tab, and we want the situation
        if account.type == Account.TYPE_SAVINGS and "Capital Expansion" in account.label:
            self.page.go_on_history_tab()

        # getting about 6 months history on new website
        if self.is_new_website and self.page:
            try:
                for x in range(0, 2):
                    form = self.page.get_form(id="I1:fm", submit='//input[@name="_FID_DoActivateSearch"]')
                    if x == 1:
                        form.update({
                            [k for k in form.keys() if "DateStart" in k][0]: (datetime.now() - relativedelta(months=7)).strftime('%d/%m/%Y'),
                            [k for k in form.keys() if "DateEnd" in k][0]: datetime.now().strftime('%d/%m/%Y')
                        })
                        [form.pop(k, None) for k in form.keys() if "_FID_Do" in k and "DoSearch" not in k]
                    form.submit()
            except (IndexError, FormNotFound):
                pass

        while self.page:
            try:
                #submit form if their is more transactions to fetch
                form = self.page.get_form(id="I1:fm")
                if self.page.doc.xpath('boolean(//a[@class="ei_loadmorebtn"])'):
                    form['_FID_DoLoadMoreTransactions'] = ""
                    form.submit()
                else:
                    break
            except (IndexError, FormNotFound):
                break
            #sometime the browser can't go further
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
        groups = [list(g) for k, g in groupby(sorted(trs, key=lambda tr: tr.date), lambda tr: tr.date)]
        trs = []
        for group in groups:
            tr = FrenchTransaction()
            tr.raw = tr.label = u"RELEVE CARTE %s" % group[0].date
            tr.amount = -sum([t.amount for t in group])
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
        cards = [page.select_card(account._card_number) for page in account._card_pages] if hasattr(account, '_card_pages') else \
                account._card_links if hasattr(account, '_card_links') else []
        for card in cards:
            card_trs = []
            for tr in self.list_operations(card, account):
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
                tr.deleted = tr.type == FrenchTransaction.TYPE_CARD_SUMMARY and \
                             differed_date.month <= tr.date.month and \
                             not hasattr(tr, '_is_manualsum')

        transactions = sorted_transactions(transactions)
        return transactions

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
    def init_transfer(self, account, to, amount, reason=None):
        if to.category != u'Interne':
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
        self.page.prepare_transfer(account, to, amount, reason)
        return self.page.handle_response(account, to, amount, reason)

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
        r.currency = u'EUR'
        r.bank_name = NotAvailable
        return r

    def continue_new_recipient(self, recipient, **params):
        if u'Clé' in params:
            self.page.post_code(params[u'Clé'])
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
        data['[t:dbt%3astring;x(11)]data_input_BIC'] = params[u'Bic']
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
        if u'Clé' in params:
            return self.continue_new_recipient(recipient, **params)
        self.recipients_list.go(subbank=self.currentSubBank)
        if self.page.has_list():
            if recipient.category not in self.page.get_recipients_list():
                raise AddRecipientError('Recipient category is not on the website available list.')
            self.page.go_list(recipient.category)
        self.page.go_to_add()
        if self.verify_pass.is_here():
            raise AddRecipientStep(self.get_recipient_object(recipient), Value(u'Clé', label=self.page.get_question()))
        else:
            return self.continue_new_recipient(recipient, **params)

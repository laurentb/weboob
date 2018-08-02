# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.url import URL
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import AccountNotFound

from .pages import (
    LoginPage, CardsPage, CardHistoryPage, IncorrectLoginPage,
    ProfileProPage, ProfileEntPage, ChangePassPage, SubscriptionPage,
)
from .json_pages import AccountsJsonPage, BalancesJsonPage, HistoryJsonPage, BankStatementPage
from .transfer_pages import (
    EasyTransferPage, RecipientsJsonPage,
)


__all__ = ['SGProfessionalBrowser', 'SGEnterpriseBrowser']


class SGPEBrowser(LoginBrowser):
    login = URL('$', LoginPage)
    cards = URL('/Pgn/.+PageID=Cartes&.+', CardsPage)
    cards_history = URL('/Pgn/.+PageID=ReleveCarte&.+', CardHistoryPage)
    change_pass = URL('/gao/changer-code-secret-expire-saisie.html',
                      '/gao/changer-code-secret-inscr-saisie.html',
                      '/gao/inscrire-utilisateur-saisie.html',
                      '/gao/changer-code-secret-reattr-saisie.html',
                      '/gae/afficherInscriptionUtilisateur.html',
                      '/gae/afficherChangementCodeSecretExpire.html',
                      ChangePassPage)

    def check_logged_status(self):
        if not self.page or self.login.is_here():
            raise BrowserIncorrectPassword()

        error = self.page.get_error()
        if error:
            raise BrowserIncorrectPassword(error)

    def do_login(self):
        if not self.password.isdigit():
            raise BrowserIncorrectPassword('Password must be 6 digits long.')

        self.login.stay_or_go()
        self.session.cookies.set('PILOTE_OOBA', 'true')
        try:
            self.page.login(self.username, self.password)
        except ClientError:
            raise BrowserIncorrectPassword()

        # force page change
        if not self.accounts.is_here():
            self.go_accounts()
        self.check_logged_status()

    def card_history(self, account, coming):
        page = 1
        while page:
            self.location('/Pgn/NavigationServlet?PageID=ReleveCarte&MenuID=%sOPF&Classeur=1&Rib=%s&Carte=%s&Date=%s&PageDetail=%s&Devise=%s' % \
                            (self.MENUID, account.id, coming['carte'], coming['date'], page, account.currency))
            for transaction in self.page.iter_transactions(date=coming['date']):
                yield transaction
            if self.page.has_next():
                page += 1
            else:
                page = False

    @need_login
    def get_cb_operations(self, account):
        self.location('/Pgn/NavigationServlet?PageID=Cartes&MenuID=%sOPF&Classeur=1&NumeroPage=1&Rib=%s&Devise=%s' % (self.MENUID, account.id, account.currency))
        for coming in self.page.get_coming_list():
            if coming['date'] == 'Non definie':
                # this is a very recent transaction and we don't know his date yet
                continue
            for tr in self.card_history(account, coming):
                yield tr

    def iter_investment(self, account):
        raise NotImplementedError()

    @need_login
    def get_profile(self):
        return self.profile.stay_or_go().get_profile()


class SGEnterpriseBrowser(SGPEBrowser):
    BASEURL = 'https://entreprises.secure.societegenerale.fr'
    LOGIN_FORM = 'auth'
    MENUID = 'BANREL'
    CERTHASH = '2231d5ddb97d2950d5e6fc4d986c23be4cd231c31ad530942343a8fdcc44bb99'

    accounts = URL('/icd/syd-front/data/syd-comptes-accederDepuisMenu.json', AccountsJsonPage)
    balances = URL('/icd/syd-front/data/syd-comptes-chargerSoldes.json', BalancesJsonPage)
    history = URL('/icd/syd-front/data/syd-comptes-chargerReleve.json',
                  '/icd/syd-front/data/syd-intraday-chargerDetail.json', HistoryJsonPage)
    history_next = URL('/icd/syd-front/data/syd-comptes-chargerProchainLotEcriture.json', HistoryJsonPage)
    profile = URL('/gae/afficherModificationMesDonnees.html', ProfileEntPage)

    subscription = URL(r'/Pgn/NavigationServlet\?MenuID=BANRELRIE&PageID=ReleveRIE&NumeroPage=1&Origine=Menu', SubscriptionPage)
    subscription_form = URL(r'Pgn/NavigationServlet', SubscriptionPage)

    def go_accounts(self):
        self.accounts.go()

    @need_login
    def get_accounts_list(self):
        accounts = []
        accounts.extend(self.accounts.stay_or_go().iter_accounts())
        for acc in self.balances.go().populate_balances(accounts):
            yield acc

    @need_login
    def iter_history(self, account):
        value = self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': 'valeur'}).get_value()
        transactions = []
        transactions.extend(self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': value}).iter_history(value=value))
        transactions.extend(self.location('/icd/syd-front/data/syd-intraday-chargerDetail.json', data={'cl500_compte': account._id}).page.iter_history())
        return iter(transactions)

    @need_login
    def iter_subscription(self):
        subscriber = self.get_profile()

        self.subscription.go()

        for sub in self.page.iter_subscription():
            sub.subscriber = subscriber.name
            account = find_object(self.get_accounts_list(), id=sub.id, error=AccountNotFound)
            sub.label = account.label

            yield sub

    @need_login
    def iter_documents(self, subscription):
        data = {
            'PageID': 'ReleveRIE',
            'MenuID': 'BANRELRIE',
            'Origine': 'Menu',
            'compteSelected': subscription.id,
        }
        self.subscription_form.go(data=data)
        return self.page.iter_documents(sub_id=subscription.id)

class SGProfessionalBrowser(SGEnterpriseBrowser):
    BASEURL = 'https://professionnels.secure.societegenerale.fr'
    LOGIN_FORM = 'auth_reco'
    MENUID = 'SBOREL'
    CERTHASH = '9f5232c9b2283814976608bfd5bba9d8030247f44c8493d8d205e574ea75148e'

    incorrect_login = URL('/authent.html', IncorrectLoginPage)
    profile = URL('/gao/modifier-donnees-perso-saisie.html', ProfileProPage)

    easy_transfer = URL('/ord-web/ord//ord-virement-simplifie-emetteur.html', EasyTransferPage)
    internal_recipients = URL('/ord-web/ord//ord-virement-simplifie-beneficiaire.html', EasyTransferPage)
    external_recipients = URL('/ord-web/ord//ord-liste-compte-beneficiaire-externes.json', RecipientsJsonPage)

    bank_statement_menu = URL('/icd/syd-front/data/syd-rce-accederDepuisMenu.json', BankStatementPage)
    bank_statement_search = URL('/icd/syd-front/data/syd-rce-lancerRecherche.json', BankStatementPage)

    date_max = None
    date_min = None

    @need_login
    def iter_subscription(self):
        profile = self.get_profile()
        subscriber = profile.name

        self.bank_statement_menu.go()
        self.date_min, self.date_max = self.page.get_min_max_date()

        return self.page.iter_subscription(subscriber=subscriber)

    def get_month_by_range(self, end_month, month_range=3, january_limit=False):
        begin_month = ((end_month - month_range) % 12) + 1

        if january_limit:
            if begin_month >=end_month:
                return 1

        return begin_month

    def exceed_date_min(self, month_min, end_month):
        if end_month <= month_min:
            return True

    def advance_month(self, end_month, end_year, month_range=3):
        new_end_month = self.get_month_by_range(end_month, month_range)
        if new_end_month > end_month:
            end_year -= 1

        begin_month = self.get_month_by_range(new_end_month, month_range)
        begin_year = end_year
        if begin_month > new_end_month:
            begin_year -= 1

        return new_end_month, end_year, begin_month, begin_year

    @need_login
    def iter_recipients(self, origin_account):
        self.easy_transfer.go()
        self.page.update_origin_account(origin_account)

        params = {
            'cl_ibanEmetteur': origin_account.iban,
            'cl_codeProduit': origin_account._product_code,
            'cl_codeSousProduit': origin_account._underproduct_code,
        }
        self.internal_recipients.go(method='POST', params=params, headers={'Content-Type': 'application/json;charset=UTF-8'})
        for internal_rcpt in self.page.iter_internal_recipients():
            yield internal_rcpt

        data = {
            'an_filtreIban': 'true',
            'an_filtreIbanSEPA': 'true',
            'an_isCredit': 'true',
            'an_isDebit': 'false',
            'an_rang': 0,
            'an_restrictFRMC': 'false',
            'cl_codeProduit': origin_account._product_code,
            'cl_codeSousProduit': origin_account._underproduct_code,
            'n_nbOccurences': '10000',
        }
        self.external_recipients.go(data=data)
        assert self.page.is_all_external_recipient(), "Some recipients are missing"
        for external_rcpt in self.page.iter_external_recipients():
            yield external_rcpt

    @need_login
    def iter_documents(self, subscribtion):
        # This quality website can only fetch documents through a form, looking for dates
        # with a range of 3 months maximum

        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', self.date_max)
        end_day = int(m.group(1))
        end_month = int(m.group(2))
        end_year = int(m.group(3))

        month_range = 3
        begin_day = 2
        begin_month = self.get_month_by_range(end_month)
        begin_year = end_year
        if begin_month > end_month:
            begin_year -= 1

        # current month
        data = {
            'dt10_dateDebut' :'%02d/%02d/%d' % (begin_day, begin_month, begin_year),
            'dt10_dateFin': '%02d/%02d/%d' % (end_day, end_month, end_year),
            'cl2000_comptes': '["%s"]' % subscribtion.id,
            'cl200_typeRecherche': 'ADVANCED',
        }
        self.bank_statement_search.go(data=data)
        for d in self.page.iter_documents():
            yield d

        # other months
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', self.date_min)
        year_min = int(m.group(3))
        month_min = int(m.group(2))
        day_min = int(m.group(1))

        end_day = 1
        is_end = False
        while not is_end:
            end_month, end_year, begin_month, begin_year = self.advance_month(end_month, end_year, month_range)

            if year_min == begin_year and self.exceed_date_min(month_min, begin_month):
                begin_day = day_min
                begin_month = month_min
                is_end = True

            data = {
                'dt10_dateDebut' :'%02d/%02d/%d' % (begin_day, begin_month, begin_year),
                'dt10_dateFin': '%02d/%02d/%d' % (end_day, end_month, end_year),
                'cl2000_comptes': '["%s"]' % subscribtion.id,
                'cl200_typeRecherche': 'ADVANCED',
            }
            self.bank_statement_search.go(data=data)

            for d in self.page.iter_documents():
                yield d

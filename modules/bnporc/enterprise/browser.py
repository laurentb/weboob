# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

import re

from datetime import datetime, timedelta

from dateutil.rrule import rrule, MONTHLY
from dateutil.relativedelta import relativedelta

from weboob.browser import LoginBrowser, need_login
from weboob.capabilities.bank import Account, Transaction
from weboob.exceptions import BrowserIncorrectPassword, BrowserForbidden
from weboob.browser.url import URL
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.date import new_date

from .pages import (
    LoginPage, AuthPage, AccountsPage, AccountHistoryViewPage, AccountHistoryPage,
    ActionNeededPage, CardListPage, CardHistoryPage, merge_cards, TransactionPage,
    TokenPage, InvestPage
)


__all__ = ['BNPEnterprise']


class BNPEnterprise(LoginBrowser):
    BASEURL = 'https://secure1.entreprises.bnpparibas.net'

    login = URL('/sommaire/jsp/identification.jsp',
                '/sommaire/generateImg', LoginPage)
    auth = URL('/sommaire/PseMenuServlet', AuthPage)
    accounts = URL('/NCCPresentationWeb/e10_soldes/liste_soldes.do', AccountsPage)
    account_history_view = URL('/NCCPresentationWeb/e10_soldes/init.do\?nccIdSelected=NCC_Soldes',
                               '/NCCPresentationWeb/e11_releve_op/init.do\?identifiant=(?P<identifiant>)'
                               '&typeSolde=(?P<type_solde>)&typeReleve=(?P<type_releve>)&typeDate=(?P<type_date>)'
                               '&dateMin=(?P<date_min>)&dateMax=(?P<date_max>)&ajax=true',
                               '/NCCPresentationWeb/e11_releve_op/init.do', AccountHistoryViewPage)
    account_coming_view = URL('/NCCPresentationWeb/m04_selectionCompteGroupe/init.do\?type=compte&identifiant=(?P<identifiant>)', AccountHistoryViewPage)
    account_history = URL('/NCCPresentationWeb/e11_releve_op/listeOperations.do\?identifiant=(?P<identifiant>)' + \
                               '&dateMin=(?P<date_min>)&dateMax=(?P<date_max>)',
                          '/NCCPresentationWeb/e11_releve_op/listeOperations.do', AccountHistoryPage)
    account_coming = URL('/NCCPresentationWeb/e12_rep_cat_op/listOperations.do\?periode=date_valeur&identifiant=(?P<identifiant>)',
                         '/NCCPresentationWeb/e12_rep_cat_op/listOperations.do', AccountHistoryPage)

    card_init = URL(r'/NCCPresentationWeb/m04_selectionCompteGroupe/init.do\?type=compteCarte&identifiant=(?P<identifiant>)', CardListPage)
    card_init2 = URL(r'https://secure1.entreprises.bnpparibas.net/NCCPresentationWeb/e13_cartes/change_common.do', CardListPage)
    card_list = URL(r'/NCCPresentationWeb/e13_cartes/liste_cartes.do\?Ligne_Encour=Global', CardListPage)
    init_card_history = URL(r'/NCCPresentationWeb/e13_encours/init.do\?Id_Carte=(?P<card_id>)&Ligne_Encour=Global', CardHistoryPage)
    transaction_detail = URL(r'/NCCPresentationWeb/e21/getOptBDDF.do', TransactionPage)
    invest = URL(r'/opcvm/lister-composition/afficher.do', InvestPage)
    token_inv = URL(r'/opcvm/lister-portefeuilles/afficher.do', TokenPage)

    card_history = URL(r'/NCCPresentationWeb/e13_encours/liste_operations.do', CardHistoryPage)

    renew_pass = URL('/sommaire/PseRedirectPasswordConnect', ActionNeededPage)

    def __init__(self, *args, **kwargs):
        super(BNPEnterprise, self).__init__(*args, **kwargs)
        self.debitinfo = {}

    def do_login(self):
        self.login.go()

        if self.login.is_here() is False:
            return

        data = {}
        data['txtAuthentMode'] = 'PASSWORD'
        data['BEFORE_LOGIN_REQUEST'] = None
        data['txtPwdUserId'] = self.username
        data['gridpass_hidden_input'] = self.page.get_password(self.password)

        self.auth.go(data=data)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def get_accounts_list(self):
        accounts = []
        try:
            marketaccount = self.token_inv.go().market_search()
        except BrowserForbidden:
            marketaccount = []
        for account in self.accounts.stay_or_go().iter_accounts():
            label_tmp = re.search(r'[0-9]+', account.label).group(0)
            if label_tmp in marketaccount:
                account.type = Account.TYPE_MARKET
            accounts.append(account)

            if account._has_cards:
                self.card_init.go(identifiant=account.iban)
                self.card_init2.go()
                self.card_list.go()
                cards = list(self.page.iter_accounts(account_id=account.id, parent_iban=account.iban))
                cards = merge_cards(cards)
                for card in cards:
                    card.parent = account
                accounts.extend(cards)

                if len(cards) != len(set(card._redacted_card for card in cards)):
                    # since transactions have only the redacted number, we wouldn't be able to distinguish the cards
                    self.logger.error('account %r has multiple cards with same redacted id', account.id)
                    assert False, 'account has multiple cards with same redacted id'

        self.logger.debug('found %d checking accounts', len([acc for acc in accounts if acc.type == Account.TYPE_CHECKING]))
        self.logger.debug('found %d card accounts', len([acc for acc in accounts if acc.type == Account.TYPE_CARD]))
        self.logger.debug('searching for immediate debit cards')
        # a card appears in the cards page only if it has coming transactions
        # thus, some card accounts may disappear occasionally

        self.debitinfo = self._guess_card_debitting(accounts)
        nb = len(accounts)
        accounts = [account for account in accounts if self.debitinfo.get(getattr(account, '_redacted_card', None)) != 'immediate']
        self.logger.debug('detected %d immediate cards', len([v for v in self.debitinfo.values() if v == 'immediate']))
        self.logger.debug('removed %d immediate card accounts', nb - len(accounts))

        return accounts

    @need_login
    def get_account(self, _id):
        for account in self.get_accounts_list():
            if account.id == _id:
                return account

    @need_login
    def iter_history(self, account):
        # warning: history of card transactions doesn't appear on card page but on checking page
        # sometimes there are single transactions, sometimes there's only a summary

        # deferred card transactions must appear in card account
        # but some card accounts may disappear from time to time (see get_accounts_list)
        # we mustn't return the transactions in checking account if card disappeared

        if account.type == Account.TYPE_CARD:
            for tr in self._iter_card_history(account):
                yield tr
            return

        for tr in self._iter_history_base(account):
            if not tr._redacted_card or self.debitinfo.get(tr._redacted_card) == 'immediate':
                yield tr

    def _iter_history_base(self, account):
        history = []
        dformat = "%Y%m%d"

        for date in rrule(MONTHLY, dtstart=(datetime.now() - relativedelta(months=3)), until=datetime.now()):
            self.account_history_view.go(identifiant=account.iban, type_solde='C', type_releve='Comptable', \
                                         type_date='O', date_min=(date + relativedelta(days=1)).strftime(dformat), \
                                         date_max=(date + relativedelta(months=1)).strftime(dformat))
            self.account_history.go(identifiant=account.iban, date_min=(date + relativedelta(days=1)).strftime(dformat), \
                                    date_max=(date + relativedelta(months=1)).strftime(dformat))

            for transaction in self.page.iter_history():
                if transaction._coming:
                    self.logger.debug('skipping coming %r', transaction.to_dict())
                    continue
                history.append(transaction)
        return sorted_transactions(history)

    def _iter_card_history(self, account):
        assert account.type == Account.TYPE_CARD
        assert account.parent.type == Account.TYPE_CHECKING
        assert account._redacted_card

        for tr in self._iter_history_base(account.parent):
            if tr._redacted_card == account._redacted_card:
                if tr.type == Transaction.TYPE_CARD:
                    tr.type = Transaction.TYPE_DEFERRED_CARD
                yield tr

    @need_login
    def iter_coming_operations(self, account):
        if account.type == Account.TYPE_CARD:
            self.accounts.go()
            self.card_init.go(identifiant=account._parent_iban)
            self.card_init2.go()
            self.card_list.go()
            self.init_card_history.go(card_id=account._index)
            self.open('/NCCPresentationWeb/m99_pagination/setStatutPagination.do?ecran=e13_encours&nbEntreesParPage=TOUS&numPage=1')
            self.card_history.go()
            for tr in self.page.iter_coming():
                yield tr
        else:
            self.account_coming_view.go(identifiant=account.iban)
            self.account_coming.go(identifiant=account.iban)
            for tr in self.page.iter_coming():
                if not tr._redacted_card or self.debitinfo.get(tr._redacted_card) == 'immediate':
                    if tr.type == Transaction.TYPE_DEFERRED_CARD:
                        tr.type = Transaction.TYPE_CARD
                    yield tr

    def _guess_card_debitting(self, accounts):
        # the site doesn't indicate if cards are immediate or deferred
        # try to guess it by looking at history of checking account

        cards = {}
        checkings = [account for account in accounts if account.type == Account.TYPE_CHECKING]
        card_account_ids = [account._redacted_card for account in accounts if account.type == Account.TYPE_CARD]
        limit = new_date(datetime.now() - timedelta(days=90))

        for account in checkings:
            card_dates = {}
            for tr in self._iter_history_base(account):
                if new_date(tr.date) < limit:
                    break
                if tr.type == Transaction.TYPE_CARD and tr._redacted_card:
                    card_dates.setdefault(tr._redacted_card, []).append((tr.date, tr.rdate))

            for card, dates in card_dates.items():
                debit_dates = set(d[0] for d in dates)
                if len(debit_dates) != len(set((d.year, d.month) for d in debit_dates)):
                    self.logger.debug('card %r has multiple debit dates per month -> immediate debit', card)
                    cards[card] = 'immediate'
                    continue

                cards[card] = 'deferred'

                # checking diff between date and rdate may not be a good clue
                # there has been a transaction with:
                # dateOpt: 2017-10-25
                # dateValeur: 2017-10-18
                # dateIntro: 2017-10-30
                # carteDateFacturette: 2017-10-13

        for card in cards:
            if cards[card] != 'immediate' and card not in card_account_ids:
                self.logger.warning("card %s seems deferred but account not found, its transactions will be skipped...", card)

        return cards

    @need_login
    def iter_investment(self, account):
        if account.type == Account.TYPE_MARKET:
            token = self.token_inv.go().get_token()
            id_invest = self.page.get_id(label=account.label)
            data = {"numeroCompte": id_invest, "_csrf": token}
            headers = {"Host": "secure1.entreprises.bnpparibas.net"}
            self.location('/opcvm/lister-composition/redirect-afficher.do', data=data, headers=headers)
            for tr in self.page.iter_investment():
                yield tr

    @need_login
    def get_profile(self):
        profile = self.account_history_view.go().get_profile()
        return profile

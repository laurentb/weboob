# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account, Investment

from .pages import LoginPage, AccountsPage, ProAccountsPage, TransactionsPage, \
                   ProTransactionsPage, IbanPage, RedirectPage, AVPage


class CreditDuNordBrowser(LoginBrowser):
    ENCODING = 'UTF-8'

    login = URL('$',
                '/.*\?.*_pageLabel=page_erreur_connexion',                        LoginPage)
    redirect = URL('/swm/redirectCDN.html',                                       RedirectPage)
    av = URL('/vos-comptes/particuliers/V1_transactional_portal_page_',           AVPage)
    accounts = URL('/vos-comptes/particuliers',
                   '/vos-comptes/particuliers/transac_tableau_de_bord',           AccountsPage)
    transactions = URL('/vos-comptes/.*/transac/particuliers',                    TransactionsPage)
    proaccounts = URL('/vos-comptes/(professionnels|entreprises)',                ProAccountsPage)
    protransactions = URL('/vos-comptes/.*/transac/(professionnels|entreprises)', ProTransactionsPage)
    loans = URL('/vos-comptes/professionnels/credit_en_cours',                    ProAccountsPage)
    iban = URL('/vos-comptes/IPT/cdnProxyResource/transacClippe/RIB_impress.asp', IbanPage)

    account_type = 'particuliers'

    def __init__(self, website, *args, **kwargs):
        super(CreditDuNordBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = "https://%s" % website

    def is_logged(self):
        return self.page is not None and not self.login.is_here() and \
            not self.page.doc.xpath(u'//b[contains(text(), "vous devez modifier votre code confidentiel")]')

    def home(self):
        if self.is_logged():
            self.location('/vos-comptes/%s' % self.account_type)
            self.location(self.page.doc.xpath(u'//a[contains(text(), "Synthèse")]')[0].attrib['href'])
        else:
            self.do_login()

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

        if not self.is_logged():
            raise BrowserIncorrectPassword()

        m = re.match('https://[^/]+/vos-comptes/(\w+).*', self.url)
        if m:
            self.account_type = m.group(1)

    @need_login
    def _iter_accounts(self):
        self.home()
        self.location(self.page.get_av_link())
        if self.av.is_here():
            for a in self.page.get_av_accounts():
                self.location(a._link, data=a._args)
                self.location(a._link.replace("_attente", "_detail_contrat_rep"), data=a._args)
                self.page.fill_diff_currency(a)
                yield a
        self.home()
        for a in self.page.get_list():
            yield a
        self.loans.go()
        for a in self.page.get_list():
            yield a

    @need_login
    def get_accounts_list(self):
        accounts = list(self._iter_accounts())

        self.page.iban_page()

        link = self.page.iban_go()

        if self.page.has_iban():
            for a in [a for a in accounts if a._acc_nb]:
                self.location(link + a._acc_nb)
                a.iban = self.page.get_iban()

        return accounts

    def get_account(self, id):
        for a in self._iter_accounts():
            if a.id == id:
                return a
        return None

    @need_login
    def iter_transactions(self, link, args, acc_type):
        if args is None:
            return

        while args is not None:
            self.location(link, data=args)

            assert self.transactions.is_here()

            for tr in self.page.get_history(acc_type):
                yield tr

            args = self.page.get_next_args(args)

    @need_login
    def get_history(self, account, coming=False):
        if coming and account.type is not Account.TYPE_CARD or account.type is Account.TYPE_LOAN:
            return []

        transactions = []
        for tr in self.iter_transactions(account._link, account._args, account.type):
            transactions.append(tr)
        return transactions

    @need_login
    def get_investment(self, account):
        investments = []

        if u'LIQUIDIT' in account.label:
            inv = Investment()
            inv.code = u'XX-Liquidity'
            inv.label = u'Liquidité'
            inv.valuation = account.balance
            investments.append(inv)
            return investments

        if not account._inv:
            return []

        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            self.location(account._link, data=account._args)
            if self.page.can_iter_investments():
                investments = [i for i in self.page.get_market_investment()]
        elif (account.type == Account.TYPE_LIFE_INSURANCE):
            self.location(account._link, data=account._args)
            self.location(account._link.replace("_attente", "_detail_contrat_rep"), data=account._args)
            if self.page.can_iter_investments():
                investments = [i for i in self.page.get_deposit_investment()]
        return investments

    @need_login
    def get_profile(self):
        self.home()
        return self.page.get_profile()

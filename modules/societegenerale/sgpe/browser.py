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


from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.url import URL
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, ErrorPage, AccountsPage, CardsPage, HistoryPage, CardHistoryPage, OrderPage, AccountsListPage
from .json_pages import AccountsJsonPage, BalancesJsonPage, HistoryJsonPage


__all__ = ['SGProfessionalBrowser', 'SGEnterpriseBrowser']


class SGPEBrowser(LoginBrowser):
    login = URL('$', LoginPage)
    cards = URL('/Pgn/.+PageID=Cartes&.+', CardsPage)
    cards_history = URL('/Pgn/.+PageID=ReleveCarte&.+', CardHistoryPage)

    def is_logged(self):
        if not self.page or self.login.is_here():
            return False

        error = self.page.get_error()
        if error is None:
            return True
        return False

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
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
        if not self.is_logged():
            raise BrowserIncorrectPassword()

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
            for tr in self.card_history(account, coming):
                yield tr

    def iter_investment(self, account):
        raise NotImplementedError()


class SGProfessionalBrowser(SGPEBrowser):
    BASEURL = 'https://professionnels.secure.societegenerale.fr'
    LOGIN_FORM = 'auth_reco'
    MENUID = 'SBOREL'
    CERTHASH = '9f5232c9b2283814976608bfd5bba9d8030247f44c8493d8d205e574ea75148e'

    accounts = URL('/Pgn/.+PageID=SoldeV3&.+', AccountsPage)
    accounts_list = URL('/Pgn/.+PageID=Compte&.+', AccountsListPage)
    history = URL('/.+PageID=ReleveCompteV3&.+',
                  '/.+PageID=ReleveEcritureIntraday&.+', HistoryPage)
    order = URL('/ord-web/ord//ord-liste-compte-emetteur.json', OrderPage)
    error = URL('/authent\.html', ErrorPage)

    def go_accounts(self, page=1):
        self.location('/Pgn/NavigationServlet?PageID=SoldeV3&MenuID=%sCPT&Classeur=%s&NumeroPage=1' % (self.MENUID, page))

    @need_login
    def get_accounts_list(self):
        self.location('/Pgn/NavigationServlet?MenuID=SBORELCPT&PageID=Compte&Classeur=1&NumeroPage=1&Origine=Menu')
        binder = range(1, self.page.get_binder_number() + 1)
        accounts_list = []
        for p in binder:
            self.go_accounts(p)
            assert self.accounts.is_here()

            for acc in self.page.get_list():
                acc._binder = p
                accounts_list.append(acc)

        self.order.go()
        for acc in accounts_list:
            acc.iban = self.page.get_iban(acc.id)
        return iter(accounts_list)

    def get_account(self, _id):
        for a in self.get_accounts_list():
            if a.id == _id:
                yield a

    def go_history(self, _id, page=1, binder=1):
        pgadd = '&page_numero_page_courante=%s' % page if page > 1 else ''
        self.location('/Pgn/NavigationServlet?PageID=ReleveCompteV3&MenuID=%sCPT&Classeur=%s&Rib=%s&NumeroPage=1%s' % (self.MENUID, binder, _id, pgadd))

    def go_today(self, _id, page=1, binder=1):
        pgadd = '&page_numero_page_courante=%s' % page if page > 1 else ''
        self.location('/Pgn/NavigationServlet?MenuID=%sOPJ&PageID=ReleveEcritureIntraday&Classeur=%s&Rib=%s&NumeroPage=1%s' % (self.MENUID, binder, _id, pgadd))

    @need_login
    def iter_history(self, account):
        # Daily Transactions.
        page = 1
        while page:
            self.go_today(account.id, page, account._binder)
            assert self.history.is_here()
            for transaction in self.page.iter_transactions():
                yield transaction
            if self.page.has_next():
                page += 1
            else:
                page = False
        page = 1
        # Other Transactions
        while page:
            self.go_history(account.id, page, account._binder)
            assert self.history.is_here()
            for transaction in self.page.iter_transactions():
                yield transaction
            if self.page.has_next():
                page += 1
            else:
                page = False


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

    def go_accounts(self):
        self.accounts.go()

    @need_login
    def get_accounts_list(self):
        accounts = []
        accounts.extend(self.accounts.stay_or_go().iter_accounts())
        return self.balances.go().populate_balances(accounts)

    @need_login
    def iter_history(self, account):
        transactions = []
        transactions.extend(self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': 'valeur'}).iter_history())
        transactions.extend(self.location('/icd/syd-front/data/syd-intraday-chargerDetail.json', data={'cl500_compte': account._id}).page.iter_history())
        return iter(transactions)

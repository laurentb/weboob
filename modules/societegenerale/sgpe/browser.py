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

from .pages import LoginPage, CardsPage, CardHistoryPage, ProfileProPage, ProfileEntPage, ChangePassPage
from .json_pages import AccountsJsonPage, BalancesJsonPage, HistoryJsonPage


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

    def is_logged(self):
        if not self.page or self.login.is_here():
            return False

        error = self.page.get_error()
        if error is None:
            return True
        return False

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


class SGProfessionalBrowser(SGEnterpriseBrowser):
    BASEURL = 'https://professionnels.secure.societegenerale.fr'
    LOGIN_FORM = 'auth_reco'
    MENUID = 'SBOREL'
    CERTHASH = '9f5232c9b2283814976608bfd5bba9d8030247f44c8493d8d205e574ea75148e'

    profile = URL('/gao/modifier-donnees-perso-saisie.html', ProfileProPage)

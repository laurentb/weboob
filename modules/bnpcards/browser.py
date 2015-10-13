# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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


from weboob.exceptions import BrowserIncorrectPassword, BrowserPasswordExpired
from weboob.browser import LoginBrowser, URL, need_login

from .pages import LoginPage, ErrorPage, AccountsPage, TransactionsPage, \
                   TiCardPage, TiHistoPage, ComingPage, HistoPage, HomePage


class BnpcartesentrepriseBrowser(LoginBrowser):
    BASEURL = 'https://www.cartesentreprise.bnpparibas.com'

    login = URL('/ce_internet_public/seConnecter.builder.do', LoginPage)
    error = URL('.*.seConnecter.event.do',
                '.*.compteGestChgPWD.builder.do',
                '/ce_internet_prive_ti/compteTituChgPWD.builder.do',
                ErrorPage)
    home = URL('/ce_internet_prive_ge/accueilInternetGe.builder.do',
               '/ce_internet_prive_ti/accueilInternetTi.builder.do', HomePage)
    accounts = URL('/ce_internet_prive_ge/carteAffaireParc.builder.do',
                   '/ce_internet_prive_ge/carteAffaireParcChange.event.do', AccountsPage)
    coming = URL('/ce_internet_prive_ge/operationEnCours.builder.do',
                 '/ce_internet_prive_ge/operationEnCours.event.do', ComingPage)
    history = URL('/ce_internet_prive_ge/operationHisto.builder.do',
                   '/ce_internet_prive_ge/operationHisto.event.do', HistoPage)
    transactions = URL('ce_internet_prive_ge/operationEnCoursDetail.builder.do.*',
                       'ce_internet_prive_ge/operationHistoDetail.builder.do.*',
                       TransactionsPage)

    ti_card = URL('/ce_internet_prive_ti/operationEnCoursDetail.builder.do',
                  '/ce_internet_prive_ti/operationEnCoursDetail.event.do.*',
                  '/ce_internet_prive_ti/pageOperationEnCoursDetail.event.do.*', TiCardPage)
    ti_histo = URL('/ce_internet_prive_ti/operationHistoDetail.builder.do',
                   '/ce_internet_prive_ti/operationHistoDetail.event.do.*',
                   '/ce_internet_prive_ti/pageOperationHistoDetail.event.do.*', TiHistoPage)
    TIMEOUT = 60.0
    CARDTYP = None

    class CorporateCard(Exception):
        pass

    def __init__(self, type, *args, **kwargs):
        super(BnpcartesentrepriseBrowser, self).__init__(*args, **kwargs)
        self.type = type
        self.do_login()

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.type, self.username, self.password)
        if self.error.is_here() or self.page.is_error():
            raise BrowserIncorrectPassword()
        if self.type == '2' and self.page.is_corporate():
            raise self.CorporateCard()

    @need_login
    def iter_accounts(self):
        if self.type == '1':
            self.ti_card.go()
        elif self.type == '2':
            self.accounts.go()
        if self.error.is_here():
            raise BrowserPasswordExpired()
        if self.type == '2':
            self.page.expand()
        return self.page.iter_accounts()

    @need_login
    def get_ti_transactions(self, account, coming=False):
        self.ti_card.go()
        self.page.expand()
        for tr in self.page.get_history():
            if coming and tr._coming:
                yield tr
            elif not coming and not tr._coming:
                yield tr
        self.ti_histo.stay_or_go()
        for period in self.page.get_periods():
            self.page.expand(period)
            for tr in self.page.get_history():
                if coming and tr._coming:
                    yield tr
                elif not coming and not tr._coming:
                    yield tr

    @need_login
    def get_transactions(self, account):
        transactions = []
        self.accounts.go()
        self.page.expand()
        accounts = list(self.page.iter_accounts())
        self.coming.go()
        self.page.expand()
        for a in accounts:
            if a.id == account.id:
                link = self.page.get_link(a.id)
                if link:
                    self.location(link)
                    transactions += self.page.get_history()
        self.history.go()
        for period in self.page.get_periods():
            self.page.expand(period)
            for a in accounts:
                if a.id == account.id:
                    link = self.page.get_link(a.id)
                    if link:
                        self.location(link)
                        transactions += self.page.get_history()
                        self.history.go()
        return iter(transactions)

    @need_login
    def get_coming(self, account):
        if self.type == '1':
            return self.get_ti_transactions(account, coming=True)
        return [t for t in self.get_transactions(account) if t._coming]


    @need_login
    def get_history(self, account):
        if self.type == '1':
            return self.get_ti_transactions(account)
        return [t for t in self.get_transactions(account) if not t._coming]

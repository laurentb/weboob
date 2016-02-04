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
                   TiHomePage, TiCardPage, TiHistoPage


__all__ = ['BnpcartesentrepriseCorporateBrowser']


class BnpcartesentrepriseCorporateBrowser(LoginBrowser):
    BASEURL = 'https://www.cartesentreprise.bnpparibas.com'

    login = URL('/ce_internet_public/seConnecter.builder.do', LoginPage)
    error = URL('.*.seConnecter.event.do',
                '.*.compteGestChgPWD.builder.do',
                '/ce_internet_prive_ti/compteTituChgPWD.builder.do',
                ErrorPage)
    acc_home = URL('/ce_internet_prive_ge/carteCorporateParc.builder.do', AccountsPage)
    accounts = URL('/ce_internet_prive_ge/operationVotreParcAfficherCorporate.event.do',
                   '/ce_internet_prive_ge/operationVotreParcAppliquerCorporate.event.do.*',
                   AccountsPage)
    com_home = URL('/ce_internet_prive_ge/operationCorporateEnCours.builder.do', AccountsPage)
    coming = URL('/ce_internet_prive_ge/operationEnCoursAfficherCorporate.event.do',
                 '/ce_internet_prive_ge/operationEnCoursAppliquerCorporate.event.do.*',
                 'ce_internet_prive_ge/operationEnCoursDetailAppliquerCorporate.event.do.*',
                 AccountsPage)
    his_home = URL('/ce_internet_prive_ge/operationCorporateHisto.builder.do', AccountsPage)
    history = URL('/ce_internet_prive_ge/operationHistoriqueAfficherCorporate.event.do',
                 '/ce_internet_prive_ge/operationHistoriqueAppliquerCorporate.event.do.*',
                 AccountsPage)
    transactions = URL('ce_internet_prive_ge/operationCorporateEnCoursDetail.builder.do.*',
                       'ce_internet_prive_ge/operationCorporateDetailHistorique.builder.do.*',
                       'ce_internet_prive_ge/operationDetail.*AppliquerCorporate.event.do.*',
                       TransactionsPage)

    ti_home = URL('/ce_internet_prive_ti/accueilInternetTi.builder.do', TiHomePage)
    ti_card = URL('/ce_internet_prive_ti/operationEnCoursDetail.builder.do',
                  '/ce_internet_prive_ti/operationEnCoursDetail.event.do.*',
                  '/ce_internet_prive_ti/pageOperationEnCoursDetail.event.do.*', TiCardPage)
    ti_histo = URL('/ce_internet_prive_ti/operationHistoDetail.builder.do',
                   '/ce_internet_prive_ti/operationHistoDetail.event.do.*',
                   '/ce_internet_prive_ti/pageOperationHistoDetail.event.do.*', TiHistoPage)
    TIMEOUT = 60.0

    def __init__(self, type, *args, **kwargs):
        super(BnpcartesentrepriseCorporateBrowser, self).__init__(*args, **kwargs)
        self.type = type

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.type, self.username, self.password)
        if self.error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        if self.type == '1':
            self.ti_card.go()
        elif self.type == '2':
            self.acc_home.go()
        if self.error.is_here():
            raise BrowserPasswordExpired()
        if self.type == '2':
            self.page.expand()
        self.accounts = [acc for acc in self.page.iter_accounts()]
        for acc in self.accounts:
            yield acc

    @need_login
    def get_ti_transactions(self, account, coming=False):
        self.ti_card.go()
        self.page.expand()
        for tr in self.page.get_transactions():
            if coming and tr._coming:
                yield tr
            elif not coming and not tr._coming:
                yield tr
        self.ti_histo.stay_or_go()
        for period in self.page.get_periods():
            self.page.expand(period)
            for tr in self.page.get_transactions():
                if coming and tr._coming:
                    yield tr
                elif not coming and not tr._coming:
                    yield tr


    @need_login
    def get_link(self, id):
        links = [l for l in self.page.get_link(id)]
        if len(links) > 0:
            return links[0]

    @need_login
    def get_coming(self, account):
        if self.type == '1':
            return self.get_ti_transactions(account, coming=True)
        if not hasattr(self, 'accounts') or not self.accounts:
            self.iter_accounts()
        self.his_home.go()
        self.page.expand()
        for a in self.accounts:
            if a.id == account.id:
                link = self.get_link(a.number)
                if link:
                    self.location(link)
                    assert self.transactions.is_here()

                    if self.page.is_not_sorted('up'):
                        self.page.sort('up')

                    transactions = [t for t in self.page.get_history() if t._coming]
                    transactions.sort(key=lambda transaction: transaction.date, reverse=True)
                    return transactions
        return iter([])


    @need_login
    def get_history(self, account):
        if self.type == '1':
            return self.get_ti_transactions(account)
        if not hasattr(self, 'accounts') or not self.accounts:
            self.iter_accounts()
        self.his_home.go()
        self.page.expand()
        for a in self.accounts:
            if a.id == account.id:
                link = self.get_link(a.number)
                if link:
                    self.location(link)
                    assert self.transactions.is_here()

                    if self.page.is_not_sorted():
                        self.page.sort()

                    transactions = [t for t in self.page.get_history() if not t._coming]
                    transactions.sort(key=lambda transaction: transaction.date, reverse=True)
                    return transactions
        return iter([])

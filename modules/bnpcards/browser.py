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

from .pages import LoginPage, ErrorPage, AccountsPage, TransactionsPage


class BnpcartesentrepriseBrowser(LoginBrowser):
    BASEURL = 'https://www.cartesentreprise.bnpparibas.com'

    login = URL('/ce_internet_public/seConnecter.builder.do', LoginPage)
    error = URL('.*.seConnecter.event.do',
                '.*.compteGestChgPWD.builder.do',
                #'/ce_internet_prive_ge/accueilInternetGe.builder.do',
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

    TIMEOUT = 30.0

    def __init__(self, type, *args, **kwargs):
        super(BnpcartesentrepriseBrowser, self).__init__(*args, **kwargs)
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
        self.acc_home.go()
        if self.error.is_here():
            raise BrowserPasswordExpired()
        self.page.expand()
        return self.page.iter_accounts()

    def get_coming(self, account):
        self.com_home.go()
        self.page.expand()
        accounts = self.page.iter_accounts()
        for a in accounts:
            if a.id == account.id:
                self.location(self.page.get_link(a.id))
                assert self.transactions.is_here()
                return self.page.get_history()
        return iter([])


    def get_history(self, account):
        self.his_home.go()
        self.page.expand()
        accounts = self.page.iter_accounts()
        for a in accounts:
            if a.id == account.id:
                self.location(self.page.get_link(a.id))
                assert self.transactions.is_here()

                if self.page.is_not_sorted():
                    self.page.sort()

                return self.page.get_history()
        return iter([])

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
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import LoginPage, ErrorPage, AccountsPage, TransactionsPage


__all__ = ['BnpcartesentrepriseCorporateBrowser']


class BnpcartesentrepriseCorporateBrowser(LoginBrowser):
    BASEURL = 'https://www.cartesentreprise.bnpparibas.com'

    login = URL('/ce_internet_public/seConnecter.builder.do', LoginPage)
    error = URL('.*.seConnecter.event.do',
                '.*.compteGestChgPWD.builder.do',
                '/ce_internet_prive_ti/compteTituChgPWD.builder.do',
                ErrorPage)
    acc_home = URL('/ce_internet_prive_ge/carteCorporateParc.builder.do', AccountsPage)
    accounts_page = URL('/ce_internet_prive_ge/operationVotreParcAfficherCorporate.event.do',
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

    TIMEOUT = 60.0


    def __init__(self, *args, **kwargs):
        super(BnpcartesentrepriseCorporateBrowser, self).__init__(*args, **kwargs)
        self.accounts = []

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.username, self.password)
        if self.error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        if not self.accounts:
            self.acc_home.go()
            if self.error.is_here():
                raise BrowserPasswordExpired()
            self.page.expand()
            for acc in self.page.iter_accounts():
                if acc.id in [a.id for a in self.accounts]:
                    # TODO apply that id to all accounts
                    acc.id = "%s_%s" % (acc.id, ''.join(acc.label.split()))
                self.accounts.append(acc)
        for acc in self.accounts:
            yield acc

    @need_login
    def get_link(self, id, owner):
        links = [l for l in self.page.get_link(id, owner)]
        if len(links) > 0:
            return links[0]

    @need_login
    def get_transactions(self, account):
        if not self.accounts:
            self.iter_accounts()

        self.his_home.go()
        self.page.expand()
        for a in self.accounts:
            if a.id == account.id:
                link = self.get_link(a.number, a._owner)
                if link:
                    self.location(link)
                    assert self.transactions.is_here()

                    # We might not be on first page.
                    self.page.assert_first_page_or_go_there()

                    if self.page.is_not_sorted():
                        self.page.sort()

                    transactions = list(self.page.get_history())
                    transactions = sorted_transactions(transactions)
                    return transactions
        return iter([])

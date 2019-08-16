# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.exceptions import BrowserIncorrectPassword, BrowserPasswordExpired
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.switch import SiteSwitch
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.compat import basestring

from .pages import LoginPage, ErrorPage, AccountsPage, TransactionsPage, \
                   TiCardPage, TiHistoPage, ComingPage, HistoPage, HomePage


class BnpcartesentrepriseBrowser(LoginBrowser):
    BASEURL = 'https://www.cartesentreprise.bnpparibas.com'

    login = URL(r'/ce_internet_public/seConnecter.builder.do', LoginPage)
    error = URL(r'.*.seConnecter.event.do',
                r'.*.compteGestChgPWD.builder.do',
                r'/ce_internet_prive_ti/compteTituChgPWD.builder.do',
                r'/ce_internet_corporate_ti/compteTituChgPWDCorporate.builder.do',
                ErrorPage)
    home = URL(r'/ce_internet_prive_ge/accueilInternetGe.builder.do',
               r'/ce_internet_(prive|corporate)_ti/accueilInternetTi(Corporate)?.builder.do', HomePage)
    accounts = URL(r'/ce_internet_prive_ge/carteAffaireParc.builder.do',
                   r'/ce_internet_prive_ge/carteAffaireParcChange.event.do',
                   r'/ce_internet_prive_ge/pageParcCarteAffaire.event.do', AccountsPage)
    coming = URL(r'/ce_internet_prive_ge/operationEnCours.builder.do',
                 r'/ce_internet_prive_ge/operationEnCours.event.do', ComingPage)
    history = URL(r'/ce_internet_prive_ge/operationHisto.builder.do',
                  r'/ce_internet_prive_ge/operationHisto.event.do', HistoPage)
    transactions = URL(r'ce_internet_prive_ge/operationEnCoursDetail.builder.do.*',
                       r'ce_internet_prive_ge/pageOperationEnCoursDetail.event.do.*',
                       r'ce_internet_prive_ge/operationHistoDetail.builder.do.*',
                       r'ce_internet_prive_ge/pageOperationHistoDetail.event.do.*',
                       TransactionsPage)

    ti_card = URL(r'/ce_internet_prive_ti/operationEnCoursDetail.builder.do',
                  r'/ce_internet_(prive|corporate)_ti/operation(Corporate)?EnCoursDetail(Afficher|Appliquer)?.event.do.*',
                  r'/ce_internet_prive_ti/pageOperationEnCoursDetail.event.do.*', TiCardPage)
    ti_corporate_card = URL(r'/ce_internet_corporate_ti/operationCorporateEnCoursDetail.builder.do', TiCardPage)
    ti_histo = URL(r'/ce_internet_prive_ti/operationHistoDetail.builder.do',
                   r'/ce_internet_(prive|corporate)_ti/operation(Corporate)?HistoDetail(Afficher|Appliquer)?.event.do.*',
                   r'/ce_internet_prive_ti/pageOperationHistoDetail.event.do.*', TiHistoPage)
    ti_corporate_histo = URL(r'/ce_internet_corporate_ti/operationCorporateHistoDetail.builder.do', TiHistoPage)
    TIMEOUT = 60.0

    def __init__(self, type, *args, **kwargs):
        super(BnpcartesentrepriseBrowser, self).__init__(*args, **kwargs)
        self.type = type
        self.is_corporate = False
        self.transactions_dict = {}

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.type, self.username, self.password)
        if self.error.is_here() or self.page.is_error():
            raise BrowserIncorrectPassword()
        if self.type == '2' and self.page.is_corporate():
            self.logger.info('Manager corporate connection')
            raise SiteSwitch('corporate')
        # ti corporate and ge corporate are not detected the same way ..
        if 'corporate' in self.page.url:
            self.logger.info('Carholder corporate connection')
            self.is_corporate = True
        else:
            self.logger.info('Cardholder connection')

    def ti_card_go(self):
        if self.is_corporate:
            self.ti_corporate_card.go()
        else:
            self.ti_card.go()

    def ti_histo_go(self):
        if self.is_corporate:
            self.ti_corporate_histo.go()
        else:
            self.ti_histo.go()

    @need_login
    def iter_accounts(self):
        if self.type == '1':
            self.ti_card_go()
        elif self.type == '2':
            self.accounts.go()

        if self.error.is_here():
            raise BrowserPasswordExpired()

        if self.type == '1':
            for account in self.page.iter_accounts(rib=None):
                self.page.expand(account=account)
                account.coming = self.page.get_balance()
                yield account
        if self.type == '2':
            for company in self.page.get_companies():
                self.accounts.stay_or_go()
                self.page.expand(company=company)
                for rib in self.page.get_rib_list():
                    self.page.expand(rib=rib, company=company)

                    accounts = list(self.page.iter_accounts(rib=rib, company=company))
                    ids = {}
                    prev_rib = None
                    for account in accounts:
                        if account.id in ids:
                            self.logger.warning('duplicate account %r', account.id)
                            account.id += '_%s' % ''.join(account.label.split())

                        if prev_rib != account._rib:
                            self.coming.go()
                            self.page.expand(rib=account._rib, company=account._company)
                        account.coming = self.page.get_balance(account)
                        prev_rib = account._rib

                        ids[account.id] = account
                        yield account

    # Could be the very same as non corporate but this shitty website seems
    # completely bugged
    def get_ti_corporate_transactions(self, account):
        if account.id not in self.transactions_dict:
            self.transactions_dict[account.id] = []
            self.ti_histo_go()
            self.page.expand(self.page.get_periods()[0], account=account, company=account._company)
            for tr in sorted_transactions(self.page.get_history()):
                self.transactions_dict[account.id].append(tr)
        return self.transactions_dict[account.id]

    def get_ti_transactions(self, account):
        self.ti_card_go()
        self.page.expand(account=account, company=account._company)
        for tr in sorted_transactions(self.page.get_history()):
            yield tr
        self.ti_histo_go()
        self.page.expand(self.page.get_periods()[0], account=account, company=account._company)
        for period in self.page.get_periods():
            self.page.expand(period, account=account, company=account._company)
            for tr in sorted_transactions(self.page.get_history()):
                yield tr

    def get_ge_transactions(self, account):
        transactions = []
        self.coming.go()
        self.page.expand(account=account, rib=account._rib, company=account._company)
        link = self.page.get_link(account)
        if link:
            self.location(link)
            transactions += self.page.get_history()
        self.history.go()
        for period in self.page.get_periods():
            self.page.expand(period, rib=account._rib, company=account._company, account=account)
            link = self.page.get_link(account)
            if link:
                self.location(link)
                transactions += self.page.get_history()
                self.history.go()
        return sorted_transactions(transactions)

    @need_login
    def get_transactions(self, account):
        if self.type == '1':
            if self.is_corporate:
                return self.get_ti_corporate_transactions(account)
            return self.get_ti_transactions(account)
        return self.get_ge_transactions(account)

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


from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.bank import Account, AccountNotFound

from .pages import (
    LoginPage, ErrorPage, AccountsPage, HistoryPage, LoanHistoryPage, RibPage,
    LifeInsuranceList, LifeInsuranceIframe, LifeInsuranceRedir,
    TitrePage, BoursePage,
)
from .spirica_browser import SpiricaBrowser


class BforbankBrowser(LoginBrowser):
    BASEURL = 'https://www.bforbank.com'

    login = URL('/connexion-client/service/login\?urlBack=%2Fespace-client', LoginPage)
    error = URL('/connexion-client/service/auth', ErrorPage)
    home = URL('/espace-client/$', AccountsPage)
    rib = URL('/espace-client/rib',
              '/espace-client/rib/(?P<id>\d+)', RibPage)
    loan_history = URL('/espace-client/livret/consultation.*', LoanHistoryPage)
    history = URL('/espace-client/consultation/operations/.*', HistoryPage)

    lifeinsurance_list = URL(r'/client/accounts/lifeInsurance/lifeInsuranceSummary.action', LifeInsuranceList)
    lifeinsurance_iframe = URL(r'/client/accounts/lifeInsurance/consultationDetailSpirica.action', LifeInsuranceIframe)
    lifeinsurance_redir = URL(r'https://assurance-vie.bforbank.com:443/sylvea/welcomeSSO.xhtml', LifeInsuranceRedir)

    titre = URL(r'/client/accounts/stocks/consultation/noFramePartenaireCATitres.action\?id=0', TitrePage)
    bourse = URL('https://bourse.bforbank.com/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis',
                 'https://bourse.bforbank.com/netfinca-titres/servlet/com.netfinca.frontcr.account.*',
                 BoursePage)

    def __init__(self, weboob, birthdate, username, password, *args, **kwargs):
        super(BforbankBrowser, self).__init__(username, password, *args, **kwargs)
        self.birthdate = birthdate
        self.accounts = None
        self.weboob = weboob

        self.spirica = SpiricaBrowser(weboob,
                                      'https://assurance-vie.bforbank.com:443/',
                                      None, None, *args, **kwargs)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()
        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.birthdate, self.username, self.password)
        if self.error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        if self.accounts is None:
            self.home.stay_or_go()
            self.accounts = list(self.page.iter_accounts())
            if self.page.RIB_AVAILABLE:
                self.rib.go().populate_rib(self.accounts)
        return iter(self.accounts)

    @need_login
    def get_history(self, account):
        if account.type == Account.TYPE_MARKET:
            bourse_account = self.get_bourse_account(account)

            self.location(bourse_account._link_id)
            assert self.bourse.is_here()
            return self.page.iter_history()
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            self.goto_spirica(account)
            return self.spirica.iter_history(account)

        self.location(account._link.replace('tableauDeBord', 'operations'))
        return self.page.get_operations()

    def goto_spirica(self, account):
        assert account.type == Account.TYPE_LIFE_INSURANCE
        self.lifeinsurance_list.go()

        if self.lifeinsurance_list.is_here():
            self.logger.debug('multiple life insurances, searching for %r', account)
            # multiple life insurances: dedicated page to choose
            for insurance_account in self.page.iter_accounts():
                self.logger.debug('testing %r', account)
                if insurance_account.id == account.id:
                    self.location(insurance_account._link)
                    assert self.lifeinsurance_iframe.is_here()
                    break
            else:
                raise AccountNotFound('account was not found in the dedicated page')
        else:
            assert self.lifeinsurance_iframe.is_here()

        self.location(self.page.get_iframe())
        assert self.lifeinsurance_redir.is_here()

        redir = self.page.get_redir()
        assert redir
        account._link = self.absurl(redir)
        self.spirica.session.cookies.update(self.session.cookies)
        self.spirica.logged = True

    def get_bourse_account(self, account):
        self.titre.go()
        assert self.titre.is_here()
        self.location(self.page.get_redir()) # "login" to bourse page

        self.bourse.go()
        assert self.bourse.is_here()

        self.logger.debug('searching account matching %r', account)
        for bourse_account in self.page.get_list():
            self.logger.debug('iterating account %r', bourse_account)
            if bourse_account.id.startswith(account.id[3:]):
                return bourse_account

    @need_login
    def iter_investment(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            self.goto_spirica(account)
            return self.spirica.iter_investment(account)
        elif account.type == Account.TYPE_MARKET:
            bourse_account = self.get_bourse_account(account)

            self.location(bourse_account._market_link)
            assert self.bourse.is_here()
            return self.page.iter_investment()

        raise NotImplementedError()

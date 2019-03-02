# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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
from time import sleep

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, NocaptchaQuestion, BrowserUnavailable
from weboob.capabilities.bank import Account
from weboob.tools.compat import basestring

from .pages import (
    LoginPage, MaintenancePage, HomePage, IncapsulaResourcePage, LoanHistoryPage, CardHistoryPage, SavingHistoryPage,
    LifeInvestmentsPage, LifeHistoryPage
)


__all__ = ['CarrefourBanqueBrowser']


class CarrefourBanqueBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://www.carrefour-banque.fr'

    login = URL('/espace-client/connexion', LoginPage)
    maintenance = URL('/maintenance', MaintenancePage)
    incapsula_ressource = URL('/_Incapsula_Resource', IncapsulaResourcePage)
    home = URL('/espace-client$', HomePage)

    loan_history = URL(r'/espace-client/pret-personnel/situation\?(.*)', LoanHistoryPage)
    saving_history = URL(
        r'/espace-client/compte-livret/solde-dernieres-operations\?(.*)',
        r'/espace-client/epargne-pass/historique-des-operations\?(.*)',
        r'/espace-client/epargne-libre/historique-des-operations\?(.*)',
        SavingHistoryPage
    )
    card_history = URL(r'/espace-client/carte-credit/solde-dernieres-operations\?(.*)', CardHistoryPage)
    life_history = URL(r'/espace-client/assurance-vie/historique-des-operations\?(.*)', LifeHistoryPage)
    life_investments = URL(r'/espace-client/assurance-vie/solde-dernieres-operations\?(.*)', LifeInvestmentsPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(CarrefourBanqueBrowser, self).__init__(*args, **kwargs)

    def locate_browser(self, state):
        pass

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if self.config['captcha_response'].get():
            data = {'g-recaptcha-response': self.config['captcha_response'].get()}
            self.incapsula_ressource.go(params={'SWCGHOEL': 'v2'}, data=data)

        self.login.go()
        if self.incapsula_ressource.is_here():
            if self.page.is_javascript:
                # wait several seconds and we'll get a recaptcha instead of obfuscated javascript code,
                # (which is simpler to resolve)
                sleep(5)
                self.login.go()

            if not self.page.is_javascript:
                # cookie session is not available
                website_key = self.page.get_recaptcha_site_key()
                website_url = self.login.build()
                raise NocaptchaQuestion(website_key=website_key, website_url=website_url)
            else:
                # we got javascript page again, this shouldn't happen
                assert False, "obfuscated javascript not managed"

        if self.maintenance.is_here():
            raise BrowserUnavailable(self.page.get_message())

        self.page.enter_login(self.username)
        self.page.enter_password(self.password)

        if not self.home.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_account_list(self):
        self.home.stay_or_go()
        cards = list(self.page.iter_card_accounts())
        life_insurances = list(self.page.iter_life_accounts())
        savings = list(self.page.iter_saving_accounts())
        loans = list(self.page.iter_loan_accounts())
        return cards + life_insurances + savings + loans

    @need_login
    def iter_investment(self, account):
        if account.type != Account.TYPE_LIFE_INSURANCE:
            raise NotImplementedError()

        self.home.stay_or_go()
        self.location(account._life_investments)
        assert self.life_investments.is_here()
        return self.page.get_investment(account)

    @need_login
    def iter_history(self, account):

        self.home.stay_or_go()
        self.location(account.url)

        if account.type == Account.TYPE_SAVINGS:
            assert self.saving_history.is_here()
        elif account.type == Account.TYPE_CARD:
            assert self.card_history.is_here()
        elif account.type == Account.TYPE_LOAN:
            assert self.loan_history.is_here()
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            assert self.life_history.is_here()
        else:
            raise NotImplementedError()

        return self.page.iter_history(account)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


import urllib

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrowserUnavailable
from weboob.capabilities.bank import Account
from weboob.browser.exceptions import BrowserHTTPNotFound

from .pages.accounts_list import AccountsList, AccountHistory, CardsList, LifeInsurance, \
    LifeInsuranceHistory, LifeInsuranceInvest, Market, ListRibPage, AdvisorPage
from .pages.login import LoginPage, BadLoginPage, ReinitPasswordPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(Browser):
    DOMAIN_LOGIN = 'particuliers.societegenerale.fr'
    CERTHASH_LOGIN = ['a84fd13e19c80b1dd70498292f983d9d0d19f88c2d35fcd21a5f310072b1d386']
    DOMAIN = 'particuliers.secure.societegenerale.fr'
    CERTHASH = '2275084c61b3d12bfd8886a4c2995fae99ee60f28ef30b11efc414ceb0ee2022'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
             'https://particuliers.societegenerale.fr/.*':  LoginPage,
             'https://.*.societegenerale.fr//acces/authlgn.html': BadLoginPage,
             'https://.*.societegenerale.fr/error403.html': BadLoginPage,
             '.*/acces/changecodeobligatoire.html': ReinitPasswordPage,
             '.*restitution/cns_listeprestation.html':      AccountsList,
             '.*restitution/cns_listeCartes.*.html.*':      CardsList,
             '.*restitution/cns_detail.*\.html.*':          AccountHistory,
             'https://.*.societegenerale.fr/lgn/url.html.*':AccountHistory,
             'https://.*.societegenerale.fr/brs/cct/comti20.html.*': Market,
             'https://.*.societegenerale.fr/asv/asvcns10.html.*': LifeInsurance,
             'https://.*.societegenerale.fr/asv/AVI/asvcns10a.html': LifeInsurance,
             'https://.*.societegenerale.fr/asv/AVI/asvcns20a.html': LifeInsuranceInvest,
             'https://.*.societegenerale.fr/asv/AVI/asvcns2[0-9]c.html': LifeInsuranceHistory,
             'https://.*.societegenerale.fr/restitution/imp_listeRib.html': ListRibPage,
             'https://.*.societegenerale.fr/com/contacts.html': AdvisorPage
            }

    def home(self):
        self.lowsslcheck(self.DOMAIN_LOGIN, self.CERTHASH_LOGIN)
        self.location('https://' + self.DOMAIN_LOGIN + '/index.html')

    def is_logged(self):
        if not self.page or self.is_on_page(LoginPage):
            return False

        error = self.page.get_error()
        if error is None:
            return True

        if error.startswith('Le service est momentan'):
            raise BrowserUnavailable(error)

        return False

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        if not self.password.isdigit() or len(self.password) != 6:
            raise BrowserIncorrectPassword()
        self.username = self.username[:8]

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/index.html', no_login=True)

        try:
            self.page.login(self.username, self.password)
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        if self.is_on_page(BadLoginPage):
            error = self.page.get_error()
            if error is None:
                raise BrowserIncorrectPassword()
            elif error.startswith('Votre session a'):
                raise BrowserUnavailable('Session has expired')
            elif error.startswith('Le service est momentan'):
                raise BrowserUnavailable(error)
            else:
                raise BrowserIncorrectPassword(error)

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        accounts = [acc for acc in self.page.get_list()]
        self.location('/restitution/imp_listeRib.html')
        if self.is_on_page(ListRibPage):
            # Caching rib url, so we don't have to go back and forth for each account
            for account in accounts:
                account._rib_url = self.page.get_rib_url(account)
            for account in accounts:
                if account._rib_url:
                    self.location(account._rib_url)
                    account.iban = self.page.get_iban()
        return accounts

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        for a in self.page.get_list():
            if a.id == id:
                return a

        return None

    def iter_history(self, account):
        if not account._link_id:
            return
        self.location(account._link_id)

        if self.is_on_page(CardsList):
            for card_link in self.page.iter_cards():
                self.location(card_link)
                for trans in self.page.iter_transactions():
                    yield trans
        elif self.is_on_page(AccountHistory):
            for trans in self.page.iter_transactions():
                yield trans

        elif self.is_on_page(LifeInsurance):
            self.location('/asv/AVI/asvcns20c.html')
            for trans in self.page.iter_transactions():
                yield trans

            # go to next page
            while self.page.document.xpath('//div[@class="net2g_asv_tableau_pager"]/a[contains(@href, "actionSuivPage")]'):
                form = self.page.document.xpath('//form[@id="operationForm"]')[0]
                data = dict((item.name, item.value or '') for item in form.inputs)
                data['a100_asv_action'] = 'actionSuivPage'
                self.location('asvcns21c.html', urllib.urlencode(data))
                for trans in self.page.iter_transactions():
                    yield trans

        else:
            self.logger.warning('This account is not supported')

    def iter_investment(self, account):
        if account.type == Account.TYPE_MARKET:
            self.location(account._link_id)

        elif account.type == Account.TYPE_LIFE_INSURANCE:
            self.location(account._link_id)
            self.location('/asv/AVI/asvcns20a.html')

        else:
            self.logger.warning('This account is not supported')
            return

        for invest in self.page.iter_investment():
            yield invest

    def get_advisor(self):
        if not self.is_on_page(AdvisorPage):
            self.location('/com/contacts.html')
        return self.page.get_advisor()

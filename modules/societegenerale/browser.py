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
from weboob.capabilities.base import NotAvailable

from .pages.accounts_list import AccountsList, AccountHistory, CardsList, LifeInsurance, \
    LifeInsuranceHistory, LifeInsuranceInvest, Market
from .pages.login import LoginPage, BadLoginPage


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
             '.*restitution/cns_listeprestation.html':      AccountsList,
             '.*restitution/cns_listeCartes.*.html.*':      CardsList,
             '.*restitution/cns_detail.*\.html.*':          AccountHistory,
             'https://.*.societegenerale.fr/lgn/url.html.*':AccountHistory,
             'https://.*.societegenerale.fr/brs/cct/comti20.html.*': Market,
             'https://.*.societegenerale.fr/asv/asvcns10.html.*': LifeInsurance,
             'https://.*.societegenerale.fr/asv/AVI/asvcns10a.html': LifeInsurance,
             'https://.*.societegenerale.fr/asv/AVI/asvcns20a.html': LifeInsuranceInvest,
             'https://.*.societegenerale.fr/asv/AVI/asvcns2[0-9]c.html': LifeInsuranceHistory,
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
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/index.html', no_login=True)

        self.page.login(self.username, self.password)

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

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        for a in self.page.get_list():
            if a.id == id:
                return a

        return None

    def iter_history(self, account):
        self.location(account._link_id)

        transactions = []
        if self.is_on_page(CardsList):
            for card_link in self.page.iter_cards():
                self.location(card_link)
                transactions += list(self.page.iter_transactions())
        elif self.is_on_page(AccountHistory):
            transactions += list(self.page.iter_transactions())

        elif self.is_on_page(LifeInsurance):
            self.location('/asv/AVI/asvcns20c.html')
            transactions += [self.set_date(trans) for trans in self.page.iter_transactions()]

            # go to next page
            while self.page.document.xpath('//div[@class="net2g_asv_tableau_pager"]/a[contains(@href, "actionSuivPage")]'):
                form = self.page.document.xpath('//form[@id="operationForm"]')[0]
                data = dict((item.name, item.value or '') for item in form.inputs)
                data['a100_asv_action'] = 'actionSuivPage'
                self.location('asvcns21c.html', urllib.urlencode(data))
                transactions += [self.set_date(trans) for trans in self.page.iter_transactions()]

        else:
            self.logger.warning('This account is not supported')

        def key(tr):
            # Can't compare datetime and date, so cast them.
            try:
                return tr.rdate.date()
            except AttributeError:
                return tr.rdate

        transactions.sort(key=key, reverse=True)
        return iter(transactions)

    def iter_investment(self, account):
        if account.type == Account.TYPE_MARKET:
            self.location(account._link_id)

        elif account.type == Account.TYPE_LIFE_INSURANCE:
            self.location(account._link_id)
            self.location('/asv/AVI/asvcns20a.html')

        else:
            self.logger.warning('This account is not supported')
            return iter([])

        return self.page.iter_investment()

    def set_date(self, trans):
        """fetch date and vdate from another page"""
        form = self.page.document.xpath('//form[@id="operationForm"]')[0]
        page_index = int(form.xpath('input[@id="a100_asv_numPage"]')[0].value)

        # go to the page containing the dates
        data = dict((item.name, item.value or '') for item in form.inputs)
        data['a100_asv_action'] = 'detail'
        data['a100_asv_indexOp'] = trans.id
        self.location('/asv/AVI/asvcns21c.html', urllib.urlencode(data))

        # process the data
        date_xpath = '//td[@class="net2g_asv_suiviOperation_element1"]/following-sibling::td'
        vdate_xpath = '//td[@class="net2g_asv_tableau_cell_date"]'
        trans.date = self.parse_date(trans, date_xpath, 1)
        trans.vdate = self.parse_date(trans, vdate_xpath, 0)

        # 'return' doesn't return but leads to the first page of the list of transactions
        data = {'a100_asv_action': 'retour', 'a100_asv_type': 'historique'}
        self.location('/asv/AVI/asvcns22c.html', urllib.urlencode(data))

        # returns to the previous page
        for i in range(page_index-1):
            form = self.page.document.xpath('//form[@id="operationForm"]')[0]
            data = dict((item.name, item.value or '') for item in form.inputs)
            data['a100_asv_action'] = 'actionSuivPage'
            self.location('asvcns21c.html', urllib.urlencode(data))

        return trans

    def parse_date(self, trans, xpath, index):
        elem = self.page.document.xpath(xpath)[index]
        if elem.text:
            return trans.parse_date(elem.text.strip())
        else:
            return NotAvailable

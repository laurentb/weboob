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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.capabilities.bank import Account
from weboob.browser.exceptions import BrowserHTTPNotFound

from .pages.accounts_list import AccountsList, AccountHistory, CardsList, LifeInsurance, \
    LifeInsuranceHistory, LifeInsuranceInvest, Market, ListRibPage, AdvisorPage
from .pages.transfer import RecipientsPage, TransferPage
from .pages.login import LoginPage, BadLoginPage, ReinitPasswordPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(LoginBrowser):
    BASEURL = 'https://particuliers.secure.societegenerale.fr'

    login = URL('https://particuliers.societegenerale.fr/index.html', LoginPage)
    bad_login = URL('\/acces/authlgn.html', '/error403.html', BadLoginPage)
    reinit = URL('/acces/changecodeobligatoire.html', ReinitPasswordPage)
    accounts = URL('/restitution/cns_listeprestation.html', AccountsList)
    cards_list = URL('/restitution/cns_listeCartes.*.html', CardsList)
    account_history = URL('/restitution/cns_detail.*\.html', '/lgn/url.html', AccountHistory)
    market = URL('/brs/cct/comti20.html', Market)
    life_insurance = URL('/asv/asvcns10.html', '/asv/AVI/asvcns10a.html', '/brs/fisc/fisca10a.html', LifeInsurance)
    life_insurance_invest = URL('/asv/AVI/asvcns20a.html', LifeInsuranceInvest)
    life_insurance_history = URL('/asv/AVI/asvcns2[0-9]c.html', LifeInsuranceHistory)
    list_rib = URL('/restitution/imp_listeRib.html', ListRibPage)
    advisor = URL('/com/contacts.html', AdvisorPage)

    recipients = URL('/personnalisation/per_cptBen_modifier_liste.html', RecipientsPage)
    transfer = URL('/virement/pas_vipon_saisie.html', '/lgn/url.html\?dup', TransferPage)

    accounts_list = None

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        if not self.password.isdigit() or len(self.password) != 6:
            raise BrowserIncorrectPassword()
        self.username = self.username[:8]

        self.login.stay_or_go()

        try:
            self.page.login(self.username, self.password)
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

        if self.login.is_here():
            raise BrowserIncorrectPassword()

        if self.bad_login.is_here():
            error = self.page.get_error()
            if error is None:
                raise BrowserIncorrectPassword()
            elif error.startswith('Votre session a'):
                raise BrowserUnavailable('Session has expired')
            elif error.startswith('Le service est momentan'):
                raise BrowserUnavailable(error)
            else:
                raise BrowserIncorrectPassword(error)

    @need_login
    def get_accounts_list(self):
        if self.accounts_list is None:
            self.accounts.stay_or_go()
            self.accounts_list = [acc for acc in self.page.get_list()]
            self.list_rib.go()
            if self.list_rib.is_here():
                # Caching rib url, so we don't have to go back and forth for each account
                for account in self.accounts_list:
                    account._rib_url = self.page.get_rib_url(account)
                for account in self.accounts_list:
                    if account._rib_url:
                        self.location(account._rib_url)
                        account.iban = self.page.get_iban()
        return iter(self.accounts_list)

    @need_login
    def iter_history(self, account):
        if not account._link_id:
            return
        self.location(account._link_id)

        if self.cards_list.is_here():
            for card_link in self.page.iter_cards():
                self.location(card_link)
                for trans in self.page.iter_transactions():
                    yield trans
        elif self.account_history.is_here():
            for trans in self.page.iter_transactions():
                yield trans

        elif self.life_insurance.is_here():
            self.location('/asv/AVI/asvcns20c.html')
            for trans in self.page.iter_transactions():
                yield trans

            # go to next page
            while self.page.doc.xpath('//div[@class="net2g_asv_tableau_pager"]/a[contains(@href, "actionSuivPage")]'):
                form = self.page.get_form('//form[@id="operationForm"]')
                form['a100_asv_action'] = 'actionSuivPage'
                form.submit()
                for trans in self.page.iter_transactions():
                    yield trans

        else:
            self.logger.warning('This account is not supported')

    @need_login
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

    @need_login
    def get_advisor(self):
        return self.advisor.stay_or_go().get_advisor()

    @need_login
    def iter_recipients(self, account):
        # Seems like all accounts can transfer on all recipients.
        for recipient in self.recipients.go().iter_recipients():
            yield recipient
        for recipient in self.transfer.go().iter_recipients(account_id=account):
            yield recipient

    @need_login
    def init_transfer(self, account, recipient, transfer):
        self.transfer.go().init_transfer(account, recipient, transfer)
        self.page.check_data_consistency(transfer)
        return self.page.create_transfer(account, recipient, transfer)

    @need_login
    def execute_transfer(self, transfer):
        self.page.confirm()
        return transfer

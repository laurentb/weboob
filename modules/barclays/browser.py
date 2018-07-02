# -*- coding: utf-8 -*-

# Copyright(C) 2012-2017 Jean Walrave
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


from __future__ import unicode_literals

from requests.exceptions import ConnectionError

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable

from .pages import (
    LoginPage, AccountsPage, AccountPage, MarketAccountPage,
    LifeInsuranceAccountPage, CardPage, IbanPDFPage,
)


class Barclays(LoginBrowser):
    VERIFY = 'certificate.pem'
    BASEURL = 'https://client.milleis.fr'

    logout = URL('https://www.milleis.fr/deconnexion')
    milleis_ajax = URL('/BconnectDesk/ajaxservletcontroller')

    login = URL('/BconnectDesk/servletcontroller',                  LoginPage)
    accounts = URL('/BconnectDesk/servletcontroller',               AccountsPage)
    account = URL('/BconnectDesk/servletcontroller',                AccountPage)
    card_account = URL('/BconnectDesk/servletcontroller',           CardPage)
    market_account = URL('/BconnectDesk/servletcontroller',         MarketAccountPage)
    life_insurance_account = URL('/BconnectDesk/servletcontroller', LifeInsuranceAccountPage)
    iban = URL('/BconnectDesk/editique',                            IbanPDFPage)

    def __init__(self, secret, *args, **kwargs):
        super(Barclays, self).__init__(*args, **kwargs)
        self.secret = secret

        # do some cache to avoid time loss
        self.cache = {'history': {}}

    def locate_browser(self, state):
        pass

    def _relogin(self):
        self.do_logout()
        self.do_login()

    def _go_to_account(self, account, refresh=False):
        if refresh:
            self.page.go_to_account(account)
        else:
            if not self.accounts.is_here():
                self.page.go_to_menu('Comptes et contrats')
                if not self.accounts.is_here(): # Sometime we can't go out from account page, so re-login
                    self._relogin()

            self.page.go_to_account(account)

    def _go_to_account_space(self, space, account):
        attrs = self.page.get_space_attrs(space)
        if attrs is None:
            return False

        token = self.page.isolate_token()
        data = {
            'MODE': 'C4__AJXButtonAction',
            'key': attrs[0][:2] + attrs[0][4:],
            attrs[1]: attrs[2],
            'C9__GETMODULENOTEPAD[1].IOGETMODULENOTEPAD[1].OUTPUTPARAMETER[1].TEXT': '',
            'id': attrs[3],
            'namespace': '',
            'controllername': 'servletcontroller',
            'disable': 'false',
            'title': 'Milleis',
            token[0]: token[1]
         }

        self.milleis_ajax.open(data=data)
        self._go_to_account(account, refresh=True)
        return True

    def _multiple_account_choice(self, account):
        accounts = [a for a in self.cache['accounts'] if a._uncleaned_id == account._uncleaned_id]
        return not any(a for a in accounts if a.id in self.cache['history'])

    def do_login(self):
        self.login.go()
        self.page.login(self.username, self.password)

        if self.page.has_error():
            raise BrowserIncorrectPassword()

        # can't login if there is ' ' in the 2 characters asked
        if not self.page.login_secret(self.secret):
            self.do_login()

        if self.login.is_here():
            raise BrowserIncorrectPassword()

    def do_logout(self):
        self.logout.go()
        self.session.cookies.clear()

    @need_login
    def iter_accounts(self):
        if not self.accounts.is_here():
            self.page.go_to_menu('Comptes et contrats')

        if not 'accounts' in self.cache:
            accounts = list(self.page.iter_accounts())
            traccounts = []

            for account in accounts:
                if account.type != Account.TYPE_LOAN:
                    self._go_to_account(account)

                if account.type == Account.TYPE_CARD:
                    if self.page.is_immediate_card():
                        account.type = Account.TYPE_CHECKING

                    if not self.page.has_history():
                        continue

                    account._attached_account = self.page.do_account_attachment([a for a in accounts if a.type == Account.TYPE_CHECKING])

                account.iban = self.iban.open().get_iban() if self.page.has_iban() else NotAvailable

                traccounts.append(account)

            self.cache['accounts'] = traccounts

        return self.cache['accounts']

    @need_login
    def iter_history(self, account):
        if account.type == Account.TYPE_CARD or (account._multiple_type and not self._multiple_account_choice(account)):
            # warning: this shit code is not idempotent ^
            return []
        elif account.type == Account.TYPE_LOAN:
            return []

        if account.id not in self.cache['history']:
            self._go_to_account(account)

            if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
                if not self._go_to_account_space('Mouvements', account):
                    self.logger.warning('cannot go to history page for %r', account)
                    return []

            history_page = self.page

            if account.type != Account.TYPE_LIFE_INSURANCE:
                for _ in range(100): # on new history page they take previous results too, so go to the last page before starts recover history
                    form = history_page.form_to_history_page()

                    if not form:
                        break

                    try:
                        history_page = self.account.open(data=form)
                    except ConnectionError: # Sometime accounts have too much history and website crash
                        # Need to relogin
                        self._relogin()

                        break
                else:
                    assert False, "Too many iterations"

            self.cache['history'][account.id] = list(history_page.iter_history()) if history_page.has_history() else []

        return self.cache['history'][account.id]

    @need_login
    def iter_coming(self, account):
        if account.type != Account.TYPE_CARD:
            raise NotImplementedError()

        self._go_to_account(account)
        return self.page.iter_history()

    @need_login
    def iter_investments(self, account):
        if account.type not in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
            raise NotImplementedError()

        self._go_to_account(account)

        if account.type == Account.TYPE_LIFE_INSURANCE:
            self._go_to_account_space('Liste supports', account)

        return self.page.iter_investments()

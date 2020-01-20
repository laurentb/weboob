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

from __future__ import unicode_literals

import datetime
from dateutil.parser import parse as parse_date

from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.browser.browsers import PagesBrowser, need_login
from weboob.browser.exceptions import HTTPNotFound, ServerError
from weboob.browser.selenium import (
    SeleniumBrowser, webdriver, IsHereCondition, AnyCondition,
    SubSeleniumMixin,
)
from weboob.browser.url import URL

from .pages import (
    AccountsPage, JsonBalances, JsonPeriods, JsonHistory,
    JsonBalances2, CurrencyPage, LoginPage, NoCardPage,
    NotFoundPage, LoginErrorPage, DashboardPage,
)


__all__ = ['AmericanExpressBrowser']


class AmericanExpressLoginBrowser(SeleniumBrowser):
    BASEURL = 'https://global.americanexpress.com'

    DRIVER = webdriver.Chrome

    # True for Production / False for debug
    HEADLESS = True

    login = URL(r'/login', LoginPage)
    login_error = URL(
        r'/login',
        r'/authentication/recovery/password',
        LoginErrorPage
    )
    dashboard = URL(r'/dashboard', DashboardPage)

    def __init__(self, config, *args, **kwargs):
        super(AmericanExpressLoginBrowser, self).__init__(*args, **kwargs)
        self.username = config['login'].get()
        self.password = config['password'].get()

    def do_login(self):
        self.login.go()
        self.wait_until_is_here(self.login)

        self.page.login(self.username, self.password)

        self.wait_until(AnyCondition(
            IsHereCondition(self.login_error),
            IsHereCondition(self.dashboard),
        ))

        if self.login_error.is_here():
            error = self.page.get_error()
            if any((
                'The User ID or Password is incorrect' in error,
                'Both the User ID and Password are required' in error,
            )):
                raise BrowserIncorrectPassword(error)
            if 'Your account has been locked' in error:
                raise ActionNeeded(error)

            assert False, 'Unhandled error : "%s"' % error


class AmericanExpressBrowser(PagesBrowser, SubSeleniumMixin):
    BASEURL = 'https://global.americanexpress.com'

    accounts = URL(r'/api/servicing/v1/member', AccountsPage)
    json_balances = URL(r'/account-data/v1/financials/balances', JsonBalances)
    json_balances2 = URL(r'/api/servicing/v1/financials/transaction_summary\?type=split_by_cardmember&statement_end_date=(?P<date>[\d-]+)', JsonBalances2)
    json_pending = URL(
        r'/account-data/v1/financials/transactions\?limit=1000&offset=(?P<offset>\d+)&status=pending',
        JsonHistory
    )
    json_posted = URL(
        r'/account-data/v1/financials/transactions\?limit=1000&offset=(?P<offset>\d+)&statement_end_date=(?P<end>[0-9-]+)&status=posted',
        JsonHistory
    )
    json_periods = URL(r'/account-data/v1/financials/statement_periods', JsonPeriods)
    currency_page = URL(r'https://www.aexp-static.com/cdaas/axp-app/modules/axp-balance-summary/4.7.0/(?P<locale>\w\w-\w\w)/axp-balance-summary.json', CurrencyPage)

    no_card = URL(r'https://www.americanexpress.com/us/content/no-card/',
                  r'https://www.americanexpress.com/us/no-card/', NoCardPage)

    not_found = URL(r'/accounts/error', NotFoundPage)

    SUMMARY_CARD_LABEL = [
        'PAYMENT RECEIVED - THANK YOU',
        'PRELEVEMENT AUTOMATIQUE ENREGISTRE-MERCI',
    ]

    SELENIUM_BROWSER = AmericanExpressLoginBrowser

    def __init__(self, config, *args, **kwargs):
        super(AmericanExpressBrowser, self).__init__(*args, **kwargs)
        self.config = config
        self.username = config['login'].get()
        self.password = config['password'].get()

    @need_login
    def iter_accounts(self):
        loc = self.session.cookies.get_dict(domain=".americanexpress.com")['axplocale'].lower()
        self.currency_page.go(locale=loc)
        currency = self.page.get_currency()

        self.accounts.go()
        account_list = list(self.page.iter_accounts(currency=currency))
        for account in account_list:
            try:
                # for the main account
                self.json_balances.go(headers={'account_tokens': account.id})
            except HTTPNotFound:
                # for secondary accounts
                self.json_periods.go(headers={'account_token': account._history_token})
                periods = self.page.get_periods()
                self.json_balances2.go(date=periods[1], headers={'account_tokens': account.id})
            self.page.fill_balances(obj=account)
            yield account

    @need_login
    def iter_history(self, account):
        self.json_periods.go(headers={'account_token': account._history_token})
        periods = self.page.get_periods()
        today = datetime.date.today()
        # TODO handle pagination
        for p in periods:
            self.json_posted.go(offset=0, end=p, headers={'account_token': account._history_token})
            for tr in self.page.iter_history(periods=periods):
                # As the website is very handy, passing account_token is not enough:
                # it will return every transactions of each account, so we
                # have to match them manually
                if tr._owner == account._idforJSON and tr.date <= today:
                    yield tr

    @need_login
    def iter_coming(self, account):
        # Coming transactions can be found in a 'pending' JSON if it exists
        # ('En attente' tab on the website), as well as in a 'posted' JSON
        # ('Enregistrées' tab on the website)

        # "pending" have no vdate and debit date is in future
        self.json_periods.go(headers={'account_token': account._history_token})
        periods = self.page.get_periods()
        date = parse_date(periods[0]).date()
        today = datetime.date.today()
        # when the latest period ends today we can't know the coming debit date
        if date != today:
            try:
                self.json_pending.go(offset=0, headers={'account_token': account._history_token})
            except ServerError as exc:
                # At certain times of the month a connection might not have pendings;
                # in that case, `json_pending.go` would throw a 502 error Bad Gateway
                error_code = exc.response.json().get('code')
                error_message = exc.response.json().get('message')
                self.logger.warning('No pendings page to access to, got error %s and message "%s" instead.', error_code, error_message)
            else:
                for tr in self.page.iter_history(periods=periods):
                    if tr._owner == account._idforJSON:
                        tr.date = date
                        yield tr

        # "posted" have a vdate but debit date can be future or past
        for p in periods:
            self.json_posted.go(offset=0, end=p, headers={'account_token': account._history_token})
            for tr in self.page.iter_history(periods=periods):
                if tr.date > today or not tr.date:
                    if tr._owner == account._idforJSON:
                        yield tr
                else:
                    return

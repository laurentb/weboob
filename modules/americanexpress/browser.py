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
from uuid import uuid4
from dateutil.parser import parse as parse_date

from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded, BrowserUnavailable
from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.exceptions import HTTPNotFound, ServerError
from weboob.browser.url import URL

from .pages import (
    AccountsPage, JsonBalances, JsonPeriods, JsonHistory,
    JsonBalances2, CurrencyPage, LoginPage, NoCardPage,
    NotFoundPage, JsDataPage, HomeLoginPage,
)


__all__ = ['AmericanExpressBrowser']


class AmericanExpressBrowser(LoginBrowser):
    BASEURL = 'https://global.americanexpress.com'

    home_login = URL(r'/login\?inav=fr_utility_logout', HomeLoginPage)
    login = URL(r'/myca/logon/emea/action/login', LoginPage)

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

    js_data = URL(r'/myca/logon/us/docs/javascript/gatekeeper/gtkp_aa.js', JsDataPage)

    no_card = URL(r'https://www.americanexpress.com/us/content/no-card/',
                  r'https://www.americanexpress.com/us/no-card/', NoCardPage)

    not_found = URL(r'/accounts/error', NotFoundPage)

    SUMMARY_CARD_LABEL = [
        'PAYMENT RECEIVED - THANK YOU',
        'PRELEVEMENT AUTOMATIQUE ENREGISTRE-MERCI',
    ]

    def __init__(self, *args, **kwargs):
        super(AmericanExpressBrowser, self).__init__(*args, **kwargs)

    def get_version(self):
        self.js_data.go()
        return self.page.get_version()

    def do_login(self):
        self.home_login.go()
        self.login.go(
            data={
                'request_type': 'login',
                'UserID': self.username,
                'Password': self.password,
                'Logon': 'Logon',
                'REMEMBERME': 'on',
                'Face': 'fr_FR',
                'DestPage': 'https://global.americanexpress.com/dashboard',
                'inauth_profile_transaction_id': 'USLOGON-%s' % str(uuid4()),
            },
            headers={
                'Referer': 'https://global.americanexpress.com/login?inav=fr_utility_logout',
            },
        )

        if self.page.get_status_code() != 0:
            error_code = self.page.get_error_code()
            message = self.page.get_error_message()
            if error_code == 'LGON001':
                raise BrowserIncorrectPassword(message)
            elif error_code == 'LGON004':
                # This error happens when the website needs the user to
                # enter his card information and reset his password.
                # There is no message returned when this error happens.
                raise ActionNeeded()
            elif error_code == 'LGON008':
                # Don't know what this error means, but if we follow the redirect
                # url it allows us to be correctly logged.
                self.location(self.page.get_redirect_url())
            elif error_code == 'LGON010':
                raise BrowserUnavailable(message)
            assert False, 'Error code "%s" (msg:"%s") not handled' % (error_code, message)

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

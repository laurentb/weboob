# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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


from weboob.capabilities.bank import AccountNotFound
from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
import ssl

from .pages import LoginPage, LoginProceedPage, LoginRedirectPage, \
                   SummaryPage, ActivityCashPage, ActivityCardPage, \
                   StatementsPage, StatementPage, LoggedInPage


__all__ = ['WellsFargo']


class WellsFargo(LoginBrowser):
    BASEURL = 'https://online.wellsfargo.com'
    login = URL('/$', LoginPage)
    login_proceed = URL('/das/cgi-bin/session.cgi\?screenid=SIGNON.*$',
                        '/login\?ERROR_CODE=.*LOB=CONS&$',
                        LoginProceedPage)
    login_redirect = URL('/das/cgi-bin/session.cgi\?screenid=SIGNON.*$',
                         '/login\?ERROR_CODE=.*LOB=CONS&$',
                         LoginRedirectPage)
    summary = URL('/das/channel/accountSummary$', SummaryPage)
    activity_cash = URL('/das/cgi-bin/session.cgi\?sessargs=.+$',
                        ActivityCashPage)
    activity_card = URL('/das/cgi-bin/session.cgi\?sessargs=.+$',
                        ActivityCardPage)
    statements = URL(
        '/das/cgi-bin/session.cgi\?sessargs=.+$',
        '/das/channel/accountActivityDDA\?action=doSetPage&page=.*$',
        StatementsPage)
    statement = URL('/das/cgi-bin/session.cgi\?sessargs=.+$',
                    StatementPage)
    unknown = URL('/.*$', LoggedInPage) # E.g. random advertisement pages.

    def do_login(self):
        self.session.cookies.clear()
        self.login.go()
        self.page.login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    def location(self, *args, **kwargs):
        """
        Wells Fargo inserts redirecting pages from time to time,
        so we should follow them whenever we see them.
        """
        r = super(WellsFargo, self).location(*args, **kwargs)
        if self.login_proceed.is_here():
            return self.page.proceed()
        elif self.login_redirect.is_here():
            return self.page.redirect()
        else:
            return r

    def prepare_request(self, req):
        """
        Wells Fargo uses TLS v1.0. See issue #1647 for details.
        """
        preq = super(WellsFargo, self).prepare_request(req)
        conn = self.session.adapters['https://'].get_connection(preq.url)
        conn.ssl_version = ssl.PROTOCOL_TLSv1
        return preq

    def get_account(self, id_):
        self.to_activity()
        if id_ not in self.page.accounts_ids():
            raise AccountNotFound()
        else:
            self.to_activity(id_)
            return self.page.get_account()

    def iter_accounts(self):
        self.to_activity()
        for id_ in self.page.accounts_ids():
            self.to_activity(id_)
            yield self.page.get_account()

    @need_login
    def to_summary(self):
        self.summary.stay_or_go()
        assert self.summary.is_here()

    def is_activity(self):
        return self.activity_cash.is_here() or self.activity_card.is_here()

    @need_login
    def to_activity(self, id_=None):
        if not self.is_activity():
            self.to_summary()
            self.page.to_activity()
            assert self.is_activity()
        if id_ and self.page.account_id() != id_:
            self.page.to_account(id_)
            assert self.is_activity()
            assert self.page.account_id() == id_

    @need_login
    def to_statements(self, id_=None, year=None):
        if not self.statements.is_here():
            self.to_summary()
            self.page.to_statements()
            assert self.statements.is_here()
        if id_ and self.page.account_id() != id_:
            self.page.to_account(id_)
            assert self.statements.is_here()
            assert self.page.account_id() == id_
        if year and self.page.year() != year:
            self.page.to_year(year)
            assert self.statements.is_here()
            assert self.page.year() == year

    @need_login
    def to_statement(self, uri):
        self.location(uri)
        assert self.statement.is_here()

    def iter_history(self, account):
        self.to_activity(account.id)
        # Skip transactions on web page if we cannot apply
        # "since last statement" filter.
        # This might be the case, for example, if Wells Fargo
        # is processing the current statement:
        # "Since your credit card account statement is being processed,
        #  transactions grouped by statement period will not be available
        #  for up to seven days."
        # (www.wellsfargo.com, 2014-07-20)
        if self.page.since_last_statement():
            assert self.page.account_id() == account.id
            while True:
                for trans in self.page.iter_transactions():
                    yield trans
                if not self.page.next_():
                    break

        self.to_statements(account.id)
        for year in self.page.years():
            self.to_statements(account.id, year)
            for stmt in self.page.statements():
                self.to_statement(stmt)
                for trans in self.page.iter_transactions():
                    yield trans

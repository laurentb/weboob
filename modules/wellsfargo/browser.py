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


from time import sleep

from weboob.capabilities.bank import AccountNotFound
from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, LoginRedirectPage, LoggedInPage, SummaryPage, \
                   DynamicPage


__all__ = ['WellsFargo']


class WellsFargo(LoginBrowser):
    BASEURL = 'https://online.wellsfargo.com'
    login = URL('/$', LoginPage)
    loginRedirect = URL('/das/cgi-bin/session.cgi\?screenid=SIGNON$',
                        LoginRedirectPage)
    loggedIn = URL('/das/cgi-bin/session.cgi\?screenid=SIGNON_PORTAL_PAUSE$',
                   '/das/cgi-bin/session.cgi\?screenid=SIGNON&LOB=CONS$',
                   '/login\?ERROR_CODE=.*LOB=CONS&$',
                   LoggedInPage)
    summary = URL('/das/channel/accountSummary$', SummaryPage)
    dynamic = URL('/das/cgi-bin/session.cgi\?sessargs=.+$',
                  '/das/channel/accountActivityDDA\?action=doSetPage&page=.*$',
                  DynamicPage)

    _pause = 1

    def do_login(self):
        self.login.go()
        self.page.login(self.username, self.password)
        if not self.loginRedirect.is_here():
            raise BrowserIncorrectPassword()

        # Sometimes Wells Fargo server returns "Session time out" error
        # right after login if we don't make a pause here.
        sleep(self._pause)
        self._pause = min(30, self._pause*2)
        self.page.redirect()
        self._pause = 1

    def get_account(self, id_):
        self.to_activity()
        if id_ not in self.page.subpage.accounts_ids():
            raise AccountNotFound()
        else:
            self.to_activity(id_)
            return self.page.subpage.get_account()

    def get_accounts(self):
        self.to_activity()
        for id_ in self.page.subpage.accounts_ids():
            self.to_activity(id_)
            yield self.page.subpage.get_account()

    @need_login
    def to_summary(self):
        self.summary.stay_or_go()
        assert self.summary.is_here()

    def is_activity(self):
        try:
            return self.page.subpage.is_activity()
        except AttributeError:
            return False

    @need_login
    def to_activity(self, id_=None):
        if not self.is_activity():
            self.to_summary()
            self.page.to_activity()
            assert self.is_activity()
        if id_ and self.page.subpage.account_id() != id_:
            self.page.subpage.to_account(id_)
            assert self.is_activity()
            assert self.page.subpage.account_id() == id_

    def is_statements(self):
        try:
            return self.page.subpage.is_statements()
        except AttributeError:
            return False

    @need_login
    def to_statements(self, id_=None, year=None):
        if not self.is_statements():
            self.to_summary()
            self.page.to_statements()
            assert self.is_statements()
        if id_ and self.page.subpage.account_id() != id_:
            self.page.subpage.to_account(id_)
            assert self.is_statements()
            assert self.page.subpage.account_id() == id_
        if year and self.page.subpage.year() != year:
            self.page.subpage.to_year(year)
            assert self.is_statements()
            assert self.page.subpage.year() == year

    def is_statement(self):
        try:
            return self.page.subpage.is_statement()
        except AttributeError:
            return False

    @need_login
    def to_statement(self, uri):
        self.location(uri)
        assert self.is_statement()

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
        if self.page.subpage.since_last_statement():
            assert self.page.subpage.account_id() == account.id
            while True:
                for trans in self.page.subpage.iter_transactions():
                    yield trans
                if not self.page.subpage.next_():
                    break

        self.to_statements(account.id)
        for year in self.page.subpage.years():
            self.to_statements(account.id, year)
            for stmt in self.page.subpage.statements():
                self.to_statement(stmt)
                for trans in self.page.subpage.iter_transactions():
                    yield trans


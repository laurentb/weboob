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
from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from .pages import LoginPage, LoginRedirectPage, LoggedInPage, SummaryPage, \
                   DynamicPage, DynamicParser
from time import sleep
from mechanize import ItemNotFoundError


__all__ = ['WellsFargo']


class WellsFargo(BaseBrowser):
    DOMAIN = 'online.wellsfargo.com'
    PROTOCOL = 'https'
    CERTHASH = ['04ee8bb37799ee3d15174c767bb453f5'
                '7b17735fdfafd38cbea0b78979bdacd9']
    ENCODING = 'UTF-8'
    PAGES = {
        '/$': LoginPage,
        '/das/cgi-bin/session.cgi\?screenid=SIGNON$': LoginRedirectPage,
        '/das/cgi-bin/session.cgi\?screenid=SIGNON_PORTAL_PAUSE$':
            LoggedInPage,
        '/das/cgi-bin/session.cgi\?screenid=SIGNON&LOB=CONS$':
            LoggedInPage,
        '/login\?ERROR_CODE=.*LOB=CONS&$': LoggedInPage,
        '/das/channel/accountSummary$': SummaryPage,
        '/das/cgi-bin/session.cgi\?sessargs=.+$':
            (DynamicPage, DynamicParser()),
        '/das/channel/accountActivityDDA\?action=doSetPage&page=.*$':
            DynamicPage
    }

    def __init__(self, *args, **kwargs):
        self._pause = 1
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('/das/channel/accountSummary')

    def is_logged(self):
        try:
            return self.page.is_logged()
        except AttributeError:
            return False

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('/', no_login=True)
        assert self.is_on_page(LoginPage)

        self.page.login(self.username, self.password)
        if not self.is_on_page(LoginRedirectPage):
            raise BrowserIncorrectPassword()

        # Sometimes Wells Fargo server returns "Session time out" error
        # right after login if we don't make a pause here.
        sleep(self._pause)
        self._pause = min(30, self._pause*2)
        self.page.redirect()
        self._pause = 1

    def get_account(self, id_):
        self.to_activity()
        if id_ not in self.page.sub_page().accounts_ids():
            raise AccountNotFound()
        else:
            self.to_activity(id_)
            return self.page.sub_page().get_account()

    def get_accounts(self):
        self.to_activity()
        for id_ in self.page.sub_page().accounts_ids():
            self.to_activity(id_)
            yield self.page.sub_page().get_account()

    def to_summary(self):
        if not self.is_on_page(SummaryPage):
            self.location('/das/channel/accountSummary')
        assert self.is_on_page(SummaryPage)

    def is_activity(self):
        try:
            return self.page.sub_page().is_activity()
        except AttributeError:
            return False

    def to_activity(self, id_=None):
        if not self.is_activity():
            self.to_summary()
            self.page.to_activity()
            assert self.is_activity()
        if id_ and self.page.sub_page().account_id() != id_:
            self.page.sub_page().to_account(id_)
            assert self.is_activity()
            assert self.page.sub_page().account_id() == id_

    def is_statements(self):
        try:
            return self.page.sub_page().is_statements()
        except AttributeError:
            return False

    def to_statements(self, id_=None, year=None):
        if not self.is_statements():
            self.to_summary()
            self.page.to_statements()
            assert self.is_statements()
        if id_ and self.page.sub_page().account_id() != id_:
            self.page.sub_page().to_account(id_)
            assert self.is_statements()
            assert self.page.sub_page().account_id() == id_
        if year and self.page.sub_page().year() != year:
            self.page.sub_page().to_year(year)
            assert self.is_statements()
            assert self.page.sub_page().year() == year

    def is_statement(self):
        try:
            return self.page.sub_page().is_statement()
        except AttributeError:
            return False

    def to_statement(self, uri):
        self.location(uri)
        assert self.is_statement()

    def iter_history(self, account):
        self.to_activity(account.id)
        try:
            self.page.sub_page().since_last_statement()
        except ItemNotFoundError:
            # Skip transactions on web page if we cannot apply
            # "since last statement" filter.
            # This might be the case, for example, if Wells Fargo
            # is processing the current statement:
            # "Since your credit card account statement is being processed,
            #  transactions grouped by statement period will not be available
            #  for up to seven days."
            # (www.wellsfargo.com, 2014-07-20)
            pass
        else:
            assert self.page.sub_page().account_id() == account.id
            while True:
                for trans in self.page.sub_page().iter_transactions():
                    yield trans
                if not self.page.sub_page().next_():
                    break

        self.to_statements(account.id)
        for year in self.page.sub_page().years():
            self.to_statements(account.id, year)
            for stmt in self.page.sub_page().statements():
                self.to_statement(stmt)
                for trans in self.page.sub_page().iter_transactions():
                    yield trans


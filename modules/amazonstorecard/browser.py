# -*- coding: utf-8 -*-

# Copyright(C) 2014-2015      Oleg Plakhotniuk
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

from .pages import SomePage, LoginPage, RecentPage, StatementsPage, \
                   StatementPage, SummaryPage


__all__ = ['AmazonStoreCard']


class AmazonStoreCard(LoginBrowser):
    BASEURL = 'https://www.onlinecreditcenter6.com'
    login = URL('/consumergen2/login.do\?accountType=plcc&clientId=amazon'
                '&langId=en&subActionId=1000$',
                '/consumergen2/consumerlogin.do.*$',
                LoginPage)
    stmts = URL('/consumergen2/ebill.do$', StatementsPage)
    recent = URL('/consumergen2/recentActivity.do$', RecentPage)
    statement = URL('/consumergen2/ebillViewPDF.do.*$', StatementPage)
    summary = URL('/consumergen2/accountSummary.do$', SummaryPage)
    unknown = URL('.*', SomePage)

    def __init__(self, config, *args, **kwargs):
        super(AmazonStoreCard, self).__init__(config['userid'].get(),
            config['password'].get(), *args, **kwargs)
        self.config = config

    def do_login(self):
        self.session.cookies.clear()
        self.login.go()
        while self.login.is_here():
            self.page.proceed(self.config)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    @need_login
    def get_account(self, id_):
        a = next(self.iter_accounts())
        if (a.id != id_):
            raise AccountNotFound()
        return a

    @need_login
    def iter_accounts(self):
        yield self.summary.go(data=SummaryPage.DATA).account()

    @need_login
    def iter_history(self, account):
        for t in self.recent.go(data=RecentPage.DATA).iter_transactions():
            yield t
        for s in self.stmts.go(data=StatementsPage.DATA).iter_statements():
            for t in s.iter_transactions():
                yield t

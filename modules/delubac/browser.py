# -*- coding: utf-8 -*-

# Copyright(C) 2013      Noe Rubinstein
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, DashboardPage, OperationsPage, LCRPage


__all__ = ['DelubacBrowser']


class DelubacBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'vbankonline.delubac.com'
    ENCODING = None

    @classmethod
    def page_url(cls, name):
        return '%s://%s/%s.do' % (cls.PROTOCOL, cls.DOMAIN, name)

    PAGES = {
        '%s://%s/(simpleIndex|index).do(\;.*)?' % (PROTOCOL, DOMAIN): LoginPage,
        '%s://%s/tbord.do(\?.*)?' % (PROTOCOL, DOMAIN): DashboardPage,
        '%s://%s/releve.do(\?.*)?' % (PROTOCOL, DOMAIN): OperationsPage,
        '%s://%s/encoursList.do(\?.*)?' % (PROTOCOL, DOMAIN): LCRPage,
    }

    PAGES_REV = {
        LoginPage: '%s://%s/index.do' % (PROTOCOL, DOMAIN),
        DashboardPage: '%s://%s/tbord.do' % (PROTOCOL, DOMAIN),
        OperationsPage: '%s://%s/releve.do' % (PROTOCOL, DOMAIN),
    }

    def stay_or_go(self, page, **kwargs):
        if not self.is_on_page(page):
            self.location(self.PAGES_REV[page], **kwargs)

        assert self.is_on_page(page)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.stay_or_go(LoginPage, no_login=True)

        self.page.login(self.username, self.password)

        self.location(self.page_url('loginSecurite')+'?_top', no_login=True)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def iter_accounts(self):
        self.stay_or_go(DashboardPage)
        return self.page.iter_accounts()

    def get_account(self, _id):
        self.stay_or_go(DashboardPage)
        return self.page.get_account(_id)

    def iter_history(self, account):
        self.stay_or_go(DashboardPage)
        self.location(account._url)

        while True:
            assert self.is_on_page(OperationsPage)
            for i in self.page.iter_history():
                yield i

            next_page = self.page.next_page()
            if not next_page:
                break

            self.location(next_page)

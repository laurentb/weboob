# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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
from .pages import LoginPage, AccountPage


__all__ = ['Paypal']


class Paypal(BaseBrowser):
    DOMAIN = 'www.paypal.com'
    PROTOCOL = 'https'
    # CERTHASH = '74429081f489cb723a82171a94350913d42727053fc86cf5bf5c3d65d39ec449'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {
        '/cgi-bin/\?cmd=_login-run$':             LoginPage,
        '/cgi-bin/\?cmd=_login-submit.+$':        LoginPage,  # wrong login
        '/cgi-bin/webscr\?cmd=_account&nav=0.0$':  AccountPage,
    }

    def home(self):
        self.location('https://' + self.DOMAIN + '/en/cgi-bin/?cmd=_login-run')

    def is_logged(self):
        # TODO Does not handle disconnect mid-session
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN + '/en/cgi-bin/?cmd=_login-run')

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_account(self, _id):
        if _id != u"1":
            return None

        if not self.is_on_page(AccountPage):
            self.location('/en/cgi-bin/webscr?cmd=_account&nav=0.0')

        return self.page.get_account()

    def get_history(self, account):
        raise NotImplementedError()

    def transfer(self, from_id, to_id, amount, reason=None):
        raise NotImplementedError()

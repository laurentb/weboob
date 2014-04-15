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
from .pages import LoginPage, AccountPage, DownloadHistoryPage, SubmitPage, HistoryParser, UselessPage, HistoryPage


__all__ = ['Paypal']


class Paypal(BaseBrowser):
    DOMAIN = 'www.paypal.com'
    PROTOCOL = 'https'
    CERTHASH = ['b8f6c76050ed3035aab08474b1da0ff783f20d114b1740e8db275fe433ff69af', '96753399cf183334cef00a72719ea8e13cfe68d1e953006348f41f884180de15']
    ENCODING = 'UTF-8'
    PAGES = {
        '/cgi-bin/webscr\?cmd=_login-run$':             LoginPage,
        '/cgi-bin/webscr\?cmd=_login-submit.+$':        LoginPage,  # wrong login
        '/cgi-bin/webscr\?cmd=_login-processing.+$':    UselessPage,
        '/cgi-bin/webscr\?cmd=_account&nav=0.0$':  AccountPage,
        '/cgi-bin/webscr\?cmd=_history-download&nav=0.3.1$':  DownloadHistoryPage,
        '/cgi-bin/webscr\?cmd=_history&nav=0.3.0$':  HistoryPage,
        '/cgi-bin/webscr\?cmd=_history&dispatch=[a-z0-9]+$':  HistoryPage,
        '/cgi-bin/webscr\?dispatch=[a-z0-9]+$': (SubmitPage, HistoryParser()),
    }

    DEFAULT_TIMEOUT = 30  # CSV export is slow

    def home(self):
        self.location('https://' + self.DOMAIN + '/en/cgi-bin/webscr?cmd=_login-run')

    def is_logged(self):
        # TODO Does not handle disconnect mid-session
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN + '/en/cgi-bin/webscr?cmd=_login-run')

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_accounts(self):
        if not self.is_on_page(AccountPage):
            self.location('/en/cgi-bin/webscr?cmd=_account&nav=0.0')

        return self.page.get_accounts()

    def get_account(self, _id):
        if not self.is_on_page(AccountPage):
            self.location('/en/cgi-bin/webscr?cmd=_account&nav=0.0')

        return self.page.get_account(_id)

    def get_history(self, account):
        self.history()
        parse = True
        while parse:
            for trans in self.page.iter_transactions(account):
                yield trans
            parse = self.page.next()

    def history(self):
        self.location('/en/cgi-bin/webscr?cmd=_history&nav=0.3.0')
        self.page.filter()
        assert self.is_on_page(HistoryPage)

    def download_history(self):
        """
        Download CSV history.
        However, it is not normalized, and sometimes the download is refused
        and sent later by mail.
        """
        self.location('/en/cgi-bin/webscr?cmd=_history-download&nav=0.3.1')
        assert self.is_on_page(DownloadHistoryPage)
        self.page.download()
        return self.page.document

    def transfer(self, from_id, to_id, amount, reason=None):
        raise NotImplementedError()

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

from .pages import LoginPage, AccountsPage, HistoryPage, UnknownPage

__all__ = ['BNPEnterprise']


class BNPEnterprise(BaseBrowser):
    DOMAIN = 'entreprises.bnpparibas.net'
    PROTOCOL = 'https'
    CERTHASH = '6789f1e08e18d6578dca88ce2e0354a99dbe7824736c01c9c4fa3b456d03b9e9'

    PAGES = {'%s://%s/NSAccess.*' % (PROTOCOL, DOMAIN): LoginPage,
             '%s://%s/UNE\?.*' % (PROTOCOL, DOMAIN): AccountsPage,
             '%s://%s/ROP\?Action=F_RELCO.+' % (PROTOCOL, DOMAIN): HistoryPage,
             '%s://%s/RLOPI\?.+' % (PROTOCOL, DOMAIN): HistoryPage,
             '%s://%s/NSFR' % (PROTOCOL, DOMAIN): UnknownPage}

    def home(self):
        self.location('%s://%s/NSAccess' % (self.PROTOCOL, self.DOMAIN))

    def is_logged(self):
        if self.page:
            if self.page.get_error() is not None:
                return False
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.home()

        self.page.login(self.username, self.password)
        self.location('/UNE?ch6=0&ch8=2000&chA=1&chh=O', no_login=True)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        # options shows accounts in their original currency
        # it's the "en capitaux" mode, not sure if it's the best
        # the "en valeur" mode is ch8=1000
        if not self.is_on_page(AccountsPage):
            self.location('/UNE?ch6=0&ch8=2000&chA=1&chh=O')
        for account in self.page.get_list():
            yield account

    def get_account(self, _id):
        for a in self.get_accounts_list():
            if a.id == _id:
                yield a

    def _get_history(self, url):
        numPage = 1
        while numPage is not None:
            self.location(url + '&chP=%s' % numPage)

            for tr in self.page.iter_history():
                yield tr

            nextNumPage = self.page.get_next_numpage()
            if nextNumPage is not None and nextNumPage <= numPage:
                self.logger.error("Currently on page %d, next page cannot be %d!" % (numPage, nextNumPage))
                return

            numPage = nextNumPage


    def iter_history(self, account):
        if account._link_id is None:
            return iter([])

        self.location('/ROP?Action=F_RELCO&ch4=%s&ch8=2000' % account._link_id)
        d1, d2 = self.page.get_date_range()

        return self._get_history('/ROP?Action=F_RELCO&ch4=%s&ch5=%s&ch9=%s&ch8=2000' % (account._link_id, d1, d2))

    def iter_coming_operations(self, account):
        if account._link_id is None:
            return

        self.location('/RLOPI?chC=%s&ch8=0000' % account.id)
        d1, d2 = self.page.get_date_range()

        for tr in self._get_history('/RLOPI?chC=%s&ch8=0000&chB=1&ch7=%s&ch9=%s' % (account.id, d1, d2)):
            if tr._coming:
                yield tr

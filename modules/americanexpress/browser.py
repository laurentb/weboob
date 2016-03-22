# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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


from urlparse import urlsplit, parse_qsl
from urllib import urlencode

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.url import URL

from .pages import LoginPage, AccountsPage, TransactionsPage, WrongLoginPage


__all__ = ['AmericanExpressBrowser']


class AmericanExpressBrowser(LoginBrowser):
    BASEURL = 'https://global.americanexpress.com'

    login = URL('/myca/logon/.*', LoginPage)
    wrong_login = URL('/myca/fuidfyp/emea/.*', WrongLoginPage)
    accounts = URL('/myca/intl/isummary/.*', AccountsPage)
    transactions = URL('/myca/intl/estatement/.*', TransactionsPage)


    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.login.is_here():
            self.location('/myca/logon/emea/action?request_type=LogonHandler&DestPage=https%3A%2F%2Fglobal.americanexpress.com%2Fmyca%2Fintl%2Facctsumm%2Femea%2FaccountSummary.do%3Frequest_type%3D%26Face%3Dfr_FR%26intlink%3Dtopnavvotrecompteneligne-HPmyca&Face=fr_FR&Info=CUExpired')

        self.page.login(self.username, self.password)
        if self.wrong_login.is_here() or self.login.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def go_on_accounts_list(self):
        form = self.page.get_form(name='leftnav')
        form.url = '/myca/intl/acctsumm/emea/accountSummary.do'
        form.submit()

    @need_login
    def get_accounts_list(self):
        if not self.accounts.is_here():
            self.go_on_accounts_list()
        return self.page.get_list()

    @need_login
    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a
        return None

    @need_login
    def get_history(self, account):
        if not self.accounts.is_here():
            self.go_on_accounts_list()

        url = account._link
        if not url:
            return

        while url is not None:
            if self.accounts.is_here():
                self.location(url)
            else:
                form = self.page.get_form(name='leftnav')
                form.url = url
                form.submit()

            assert self.transactions.is_here()

            for tr in self.page.get_history(account.currency):
                yield tr

            if self.page.is_last():
                url = None
            else:
                v = urlsplit(url)
                args = dict(parse_qsl(v.query))
                args['BPIndex'] = int(args['BPIndex']) + 1
                url = '%s?%s' % (v.path, urlencode(args))

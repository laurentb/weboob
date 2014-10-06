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

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, TransactionsPage


__all__ = ['AmericanExpressBrowser']


class AmericanExpressBrowser(Browser):
    DOMAIN = 'global.americanexpress.com'
    PROTOCOL = 'https'
    ENCODING = 'ISO-8859-1'
    PAGES = {'https://global.americanexpress.com/myca/logon/.*':            LoginPage,
             'https://global.americanexpress.com/myca/intl/acctsumm/.*':    AccountsPage,
             'https://global.americanexpress.com/myca/intl/estatement/.*':  TransactionsPage,
            }

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        if self.is_logged():
            self.location(self.buildurl('/myca/intl/acctsumm/emea/accountSummary.do'))
        else:
            self.login()

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location(self.absurl('/myca/logon/emea/action?request_type=LogonHandler&DestPage=https%3A%2F%2Fglobal.americanexpress.com%2Fmyca%2Fintl%2Facctsumm%2Femea%2FaccountSummary.do%3Frequest_type%3D%26Face%3Dfr_FR%26intlink%3Dtopnavvotrecompteneligne-HPmyca&Face=fr_FR&Info=CUExpired'), no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def go_on_accounts_list(self):
        self.select_form(name='leftnav')
        self.form.action = self.absurl('/myca/intl/acctsumm/emea/accountSummary.do')
        self.submit()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.go_on_accounts_list()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        if not self.is_on_page(AccountsPage):
            self.go_on_accounts_list()

        url = account._link

        while url is not None:
            self.select_form(name='leftnav')
            self.form.action = self.absurl(url)
            self.submit()

            assert self.is_on_page(TransactionsPage)

            for tr in self.page.get_history():
                yield tr

            if self.page.is_last():
                url = None
            else:
                v = urlsplit(url)
                args = dict(parse_qsl(v.query))
                args['BPIndex'] = int(args['BPIndex']) + 1
                url = self.buildurl(v.path, **args)

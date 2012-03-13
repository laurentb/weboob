# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
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


from weboob.tools.browser import BaseBrowser
from .pages import AccountsList, LoginPage, LoginPage2, \
                   AccountHistoryCC, AccountHistoryLA


__all__ = ['Ing']


class Ing(BaseBrowser):
    DOMAIN = 'secure.ingdirect.fr'
    PROTOCOL = 'https'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*displayTRAccountSummary.*':   AccountsList,
             '.*displayLogin.jsf':            LoginPage,
             '.*displayLogin.jsf.*':          LoginPage2,
             '.*accountDetail.jsf.*':         AccountHistoryCC,
             '.*displayTRHistoriqueLA.*':     AccountHistoryLA
            }

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday', None)
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://secure.ingdirect.fr/public/displayLogin.jsf')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.birthday, basestring)
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://secure.ingdirect.fr/\
                           public/displayLogin.jsf')

        self.page.prelogin(self.username, self.birthday)
        self.page.login(self.password)

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/general?command=displayTRAccountSummary')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/general?command=displayTRAccountSummary')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, id):
        account = self.get_account(id)
        # The first and the second letter of the label are the account type
        if account.label[0:2] == "CC":
            self.location('https://secure.ingdirect.fr/\
                          protected/pages/cc/accountDetail.jsf')
        elif account.label[0:2] == "LA":
            # we want "displayTRHistoriqueLA" but this fucking page
            # is not directly available...
            self.location('https://secure.ingdirect.fr/\
                           general?command=goToAccount&account=%d&zone=COMPTE'\
                            % int(id))
        else:
            raise NotImplementedError()
        return self.page.get_transactions()

    # TODO
    # def get_coming_operations

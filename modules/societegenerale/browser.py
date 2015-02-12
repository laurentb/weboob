# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrowserUnavailable

from .pages.accounts_list import AccountsList, AccountHistory, CardsList
from .pages.login import LoginPage, BadLoginPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(Browser):
    DOMAIN_LOGIN = 'particuliers.societegenerale.fr'
    CERTHASH_LOGIN = ['7c13aac3a32e10c8210aa72612a0f4e7a2d11773b69b9d36b8e013b82d0c5b64']
    DOMAIN = 'particuliers.secure.societegenerale.fr'
    CERTHASH = 'b3d3f4afdbecf5cae20692e4ba5f1712fc00e16e732c0ed7cc76aa8d96a4833d'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
             'https://particuliers.societegenerale.fr/.*':  LoginPage,
             'https://.*.societegenerale.fr//acces/authlgn.html': BadLoginPage,
             'https://.*.societegenerale.fr/error403.html': BadLoginPage,
             '.*restitution/cns_listeprestation.html':      AccountsList,
             '.*restitution/cns_listeCartes.*.html.*':      CardsList,
             '.*restitution/cns_detail.*\.html.*':          AccountHistory,
             'https://.*.societegenerale.fr/lgn/url.html.*':AccountHistory,
            }

    def __init__(self, *args, **kwargs):
        self.lowsslcheck(self.DOMAIN_LOGIN, self.CERTHASH_LOGIN)
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://' + self.DOMAIN_LOGIN + '/index.html')

    def is_logged(self):
        if not self.page or self.is_on_page(LoginPage):
            return False

        error = self.page.get_error()
        if error is None:
            return True

        if error.startswith('Le service est momentan'):
            raise BrowserUnavailable(error)

        return False

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/index.html', no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        if self.is_on_page(BadLoginPage):
            error = self.page.get_error()
            if error is None:
                raise BrowserIncorrectPassword()
            elif error.startswith('Votre session a'):
                raise BrowserUnavailable('Session has expired')
            elif error.startswith('Le service est momentan'):
                raise BrowserUnavailable(error)
            else:
                raise BrowserIncorrectPassword(error)

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        for a in self.page.get_list():
            if a.id == id:
                return a

        return None

    def iter_history(self, account):
        self.location(account._link_id)

        transactions = []
        if self.is_on_page(CardsList):
            for card_link in self.page.iter_cards():
                self.location(card_link)
                transactions += list(self.page.iter_transactions(coming=True))
        elif self.is_on_page(AccountHistory):
            transactions += list(self.page.iter_transactions(coming=(account.type == account.TYPE_CARD)))
        else:
            self.logger.warning('This account is not supported')

        def key(tr):
            # Can't compare datetime and date, so cast them.
            try:
                return tr.rdate.date()
            except AttributeError:
                return tr.rdate

        transactions.sort(key=key, reverse=True)
        return iter(transactions)

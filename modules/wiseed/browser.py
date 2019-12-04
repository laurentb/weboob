# -*- coding: utf-8 -*-

# Copyright(C) 2019      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, need_login, URL, StatesMixin
from weboob.capabilities.bank import Account

from .pages import LoginPage, LandPage, InvestPage


# TODO implement documents and profile

class WiseedBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://www.wiseed.com'

    login = URL('/fr/connexion', LoginPage)
    landing = URL('/fr/projets-en-financement', LandPage)
    invests = URL('/fr/compte/portefeuille', InvestPage)

    def do_login(self):
        self.login.go()
        self.page.do_login(self.username, self.password)

        if self.login.is_here():
            self.page.raise_error()

        assert self.landing.is_here()

    @need_login
    def iter_accounts(self):
        self.invests.stay_or_go()

        acc = Account()
        acc.id = '_wiseed_'
        acc.type = Account.TYPE_MARKET
        acc.number = self.page.get_user_id()
        acc.label = 'WiSEED'
        acc.currency = 'EUR'
        # unfortunately there's little data
        acc.balance = sum(inv.valuation for inv in self.iter_investment())

        return [acc]

    @need_login
    def iter_investment(self):
        self.invests.stay_or_go()

        yield self.page.get_liquidities()

        for inv in self.page.iter_funded_bond():
            yield inv

        for inv in self.page.iter_funded_stock():
            yield inv

        for inv in self.page.iter_funding():
            yield inv

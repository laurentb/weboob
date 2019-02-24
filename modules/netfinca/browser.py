# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget-Insight
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


from weboob.browser import LoginBrowser, URL
from weboob.exceptions import BrowserUnavailable

from .pages import InvestmentsPage, AccountsPage


class NetfincaBrowser(LoginBrowser):
    accounts = URL(r'/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis', AccountsPage)
    investments = URL(r'/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal\?nump=(?P<nump_id>.*)', InvestmentsPage)

    def do_login(self):
        raise BrowserUnavailable()

    def iter_accounts(self):
        self.accounts.stay_or_go()
        return self.page.get_accounts()

    def iter_investments(self, account):
        self.accounts.stay_or_go()

        nump_id = self.page.get_nump_id(account)
        self.investments.go(nump_id=nump_id)

        for invest in self.page.get_investments(account_currency=account.currency):
            yield invest

        liquidity = self.page.get_liquidity()
        if liquidity:
            yield liquidity

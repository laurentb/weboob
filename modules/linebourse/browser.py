# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent Ardisson
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import time

from weboob.browser import LoginBrowser, URL
from weboob.exceptions import BrowserUnavailable

from .pages import (
    MessagePage, InvestmentPage, HistoryPage, BrokenPage,
    MainPage, FirstConnectionPage,
)

from .api.pages import (
    PortfolioPage, NewWebsiteFirstConnectionPage,
    AccountCodesPage, HistoryAPIPage,
)


def get_timestamp():
    return '{}'.format(int(time.time() * 1000))  # in milliseconds


class LinebourseBrowser(LoginBrowser):
    BASEURL = 'https://www.linebourse.fr'

    main = URL(r'/Main$', MainPage)
    first = URL(r'/GuidesPremiereConnexion$', FirstConnectionPage)
    invest = URL(r'/Portefeuille$', r'/Portefeuille\?compte=(?P<id>[^&]+)', InvestmentPage)
    message = URL(r'/DetailMessage.*', MessagePage)
    history = URL(r'/HistoriqueOperations',
                  r'/HistoriqueOperations\?compte=(?P<id>[^&]+)&devise=EUR&modeTri=7&sensTri=-1&periode=(?P<period>\d+)', HistoryPage)
    useless = URL(r'/ReroutageSJR', MessagePage)
    broken = URL(r'.*/timeout.html$', BrokenPage)

    def __init__(self, baseurl, *args, **kwargs):
        super(LinebourseBrowser, self).__init__('', '', *args, **kwargs)
        self.BASEURL = baseurl

    def do_login(self):
        raise BrowserUnavailable()

    def iter_investment(self, account_id):
        self.main.go()
        self.invest.go()
        if self.message.is_here():
            self.page.submit()
            self.invest.go()

        if self.broken.is_here():
            return iter([])

        assert self.invest.is_here()
        if not self.page.is_on_right_portfolio(account_id):
            self.invest.go(id=self.page.get_compte(account_id))
        return self.page.iter_investments()

    # Method used only by bp module
    def get_liquidity(self, account_id):
        self.main.go()
        self.invest.go()
        if self.message.is_here():
            self.page.submit()
            self.invest.go()

        if self.broken.is_here():
            return iter([])

        assert self.invest.is_here()
        if not self.page.is_on_right_portfolio(account_id):
            self.invest.go(id=self.page.get_compte(account_id))

        return self.page.get_liquidity()

    def iter_history(self, account_id):
        self.main.go()
        self.history.go()
        if self.message.is_here():
            self.page.submit()
            self.history.go()

        if self.broken.is_here():
            return

        assert self.history.is_here()

        if not self.page.is_on_right_portfolio(account_id):
            self.history.go(id=self.page.get_compte(account_id), period=0)

        periods = self.page.get_periods()

        for period in periods:
            self.history.go(id=self.page.get_compte(account_id), period=period)
            for tr in self.page.iter_history():
                yield tr


class LinebourseAPIBrowser(LoginBrowser):
    BASEURL = 'https://www.offrebourse.com'

    new_website_first = URL(r'/rest/premiereConnexion', NewWebsiteFirstConnectionPage)
    account_codes = URL(r'/rest/compte/liste/vide/0', AccountCodesPage)

    # The API works with an encrypted account_code that starts with 'CRY'
    portfolio = URL(r'/rest/portefeuille/(?P<account_code>CRY[\w\d]+)/vide/true/false', PortfolioPage)
    history = URL(r'/rest/historiqueOperations/(?P<account_code>CRY[\w\d]+)/0/7/1', HistoryAPIPage)  # TODO: not sure if last 3 path levels can be hardcoded

    def __init__(self, baseurl, *args, **kwargs):
        self.BASEURL = baseurl
        super(LinebourseAPIBrowser, self).__init__(username='', password='', *args, **kwargs)

    def get_account_code(self, account_id):
        # 'account_codes' is a JSON containing the id_contracts
        # of all the accounts present on the Linebourse space.
        params = {'_': get_timestamp()}
        self.account_codes.go(params=params)
        assert self.account_codes.is_here()
        return self.page.get_contract_number(account_id)

    def go_portfolio(self, account_id):
        account_code = self.get_account_code(account_id)
        return self.portfolio.go(account_code=account_code)

    def iter_investments(self, account_id):
        self.go_portfolio(account_id)
        assert self.portfolio.is_here()
        date = self.page.get_date()
        return self.page.iter_investments(date=date)

    def iter_history(self, account_id):
        account_code = self.get_account_code(account_id)
        self.history.go(
            account_code=account_code,
            params={'_': get_timestamp()},  # timestamp is necessary
        )
        assert self.history.is_here()
        for tr in self.page.iter_history():
            yield tr

# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent Ardisson
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

from __future__ import unicode_literals

import time
import re

from weboob.browser import LoginBrowser, URL
from weboob.exceptions import BrowserUnavailable

from .pages import (
    MessagePage, InvestmentPage, HistoryPage, BrokenPage,
    MainPage, FirstConnectionPage,
)

from .api.pages import (
    PortfolioPage, NewWebsiteFirstConnectionPage, ConfigurationPage,
    HistoryAPIPage,
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
    config = URL(r'/rest/configuration', ConfigurationPage)

    # The API works with an encrypted id_contract that starts with 'CRY'
    portfolio = URL(r'/rest/portefeuille/(?P<id_contract>CRY[\w\d]+)/vide/true/false', PortfolioPage)
    history = URL(r'/rest/historiqueOperations/(?P<id_contract>CRY[\w\d]+)/0/7/1', HistoryAPIPage)  # TODO: not sure if last 3 path levels can be hardcoded

    def __init__(self, baseurl, *args, **kwargs):
        self.BASEURL = baseurl
        self.id_contract = None  # encrypted contract number used to browse between pages

        super(LinebourseAPIBrowser, self).__init__(username='', password='', *args, **kwargs)

    def go_portfolio(self):
        self.config.go()
        self.id_contract = self.page.get_contract_number()
        return self.portfolio.go(id_contract=self.id_contract)

    def iter_investments(self):
        self.go_portfolio()
        assert self.portfolio.is_here()
        date = self.page.get_date()
        return self.page.iter_investments(date=date)

    def iter_history(self):
        assert re.match(r'CRY[\w\d]+', self.id_contract)
        self.history.go(
            id_contract=self.id_contract,
            params={'_': get_timestamp()},  # timestamp is necessary
        )
        assert self.history.is_here()

        # Didn't find a connection with transactions
        # TODO: implement corresponding pages
        if self.page.has_history():
            assert False, 'please implement iter_history'
        return []

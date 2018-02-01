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

from weboob.browser import LoginBrowser, URL
from weboob.exceptions import BrowserUnavailable
from weboob.tools.compat import quote_plus

from .pages import (
    MessagePage, InvestmentPage, HistoryPage, BrokenPage,
    MainPage, FirstConnectionPage
)


class LinebourseBrowser(LoginBrowser):
    BASEURL = 'https://www.linebourse.fr'

    main = URL(r'/Main$', MainPage)
    first = URL(r'/GuidesPremiereConnexion$', FirstConnectionPage)
    invest = URL(r'/Portefeuille$', r'/Portefeuille\?compte=(?P<id>[^&]+)', InvestmentPage)
    message = URL(r'/DetailMessage.*', MessagePage)
    history = URL(r'/HistoriqueOperations',
                  r'/HistoriqueOperations\?compte=(?P<id>[^&]+)&devise=EUR&modeTri=7&sensTri=-1&periode=(?P<period>\d+)',
                  HistoryPage)
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
        return self.page.iter_investment()

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
            self.history.go(id=quote_plus(self.page.get_compte(account_id)), period=0)

        periods = self.page.get_periods()

        for period in periods:
            self.history.go(id=quote_plus(self.page.get_compte(account_id)), period=period)
            for tr in self.page.iter_history():
                yield tr

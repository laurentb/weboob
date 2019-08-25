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

import datetime

from weboob.browser import LoginBrowser, URL, need_login
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.capabilities.bank import Investment

from .pages import (
    LoginPage, SummaryPage, GSummaryPage, ProfilePage, ComingPage,
)


class AttrURL(URL):
    def build(self, *args, **kwargs):
        import re

        for pattern in self.urls:
            regex = re.compile(pattern)

            for k in regex.groupindex:
                if hasattr(self.browser, k) and k not in kwargs:
                    kwargs[k] = getattr(self.browser, k)

        return super(AttrURL, self).build(*args, **kwargs)


class LendosphereBrowser(LoginBrowser):
    BASEURL = 'https://www.lendosphere.com'

    login = URL(r'/membres/se-connecter', LoginPage)
    dashboard = AttrURL(r'/membres/(?P<user_id>[a-z0-9-]+)/tableau-de-bord', SummaryPage)
    global_summary = AttrURL(r'/membres/(?P<user_id>[a-z0-9-]+)/dashboard_global_info', GSummaryPage)
    coming = AttrURL(r'/membres/(?P<user_id>[a-z0-9-]+)/mes-echeanciers.csv', ComingPage)
    profile = AttrURL(r'/membres/(?P<user_id>[a-z0-9-]+)', ProfilePage)

    def do_login(self):
        self.login.go()
        self.page.do_login(self.username, self.password)

        if self.login.is_here():
            self.page.raise_error()

        self.user_id = self.page.params['user_id']

    @need_login
    def iter_accounts(self):
        self.global_summary.go()
        return [self.page.get_account()]

    @need_login
    def iter_investment(self, account):
        today = datetime.date.today()

        self.coming.go()

        # unfortunately there doesn't seem to be a page indicating what's
        # left to be repaid on each project, so let's sum...
        valuations = {}
        commissions = {}
        for tr in self.page.iter_transactions():
            if tr.date <= today:
                continue

            if tr.raw not in valuations:
                valuations[tr.raw] = tr.amount
                commissions[tr.raw] = tr.commission
            else:
                valuations[tr.raw] += tr.amount
                commissions[tr.raw] += tr.commission

        for label, value in valuations.items():
            inv = Investment()
            inv.label = label
            inv.valuation = value
            inv.diff = commissions[label]
            yield inv

        yield create_french_liquidity(account._liquidities)

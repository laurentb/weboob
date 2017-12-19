# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, DetailsPage, MaintenancePage


class SpiricaBrowser(LoginBrowser):
    TIMEOUT = 60

    login = URL('/securite/login.xhtml', LoginPage)
    accounts = URL('/sylvea/client/synthese.xhtml', AccountsPage)
    details = URL('/sylvea/contrat/consultationContratEpargne.xhtml', DetailsPage)
    maintenance = URL('/maintenance.html', MaintenancePage)

    def __init__(self, website, *args, **kwargs):
        super(SpiricaBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.cache = {}
        self.cache['invs'] = {}
        self.cache['trs'] = {}

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            error = self.page.get_error()
            raise BrowserIncorrectPassword(error)

    def get_subscription_list(self):
        return iter([])

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            self.cache['accs'] = [a for a in self.accounts.stay_or_go().iter_accounts()]
        return self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            # Get form to show PRM
            self.location(account.url)
            self.page.goto_unitprice()
            invs = [i for i in self.page.iter_investment()]
            invs_pm = [i for i in self.page.iter_pm_investment()]
            self.fill_from_list(invs, invs_pm)
            self.cache['invs'][account.id] = invs
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        if account.id not in self.cache['trs']:
            self.location(account.url)
            self.page.go_historytab()
            # Get form to show all transactions
            self.page.go_historyall()
            trs = [t for t in self.page.iter_history()]
            self.cache['trs'][account.id] = trs
        return self.cache['trs'][account.id]

    def fill_from_list(self, invs, objects_list):
        matching_fields = ['code', 'unitvalue', 'label', '_gestion_type']
        for inv in invs:
            obj_from_list = [o for o in objects_list if all(getattr(o, field) == getattr(inv, field) for field in matching_fields)]
            assert len(obj_from_list) == 1
            for name, field_value in obj_from_list[0].iter_fields():
                if field_value:
                    setattr(inv, name, field_value)

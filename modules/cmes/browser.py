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


from weboob.exceptions import  BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login

from .pages import (
    LoginPage, AccountsPage, FCPEInvestmentPage,
    CCBInvestmentPage, HistoryPage,
    )


class CmesBrowser(LoginBrowser):
    BASEURL = 'https://www.cic-epargnesalariale.fr'

    login = URL('/fr/identification/authentification.html', LoginPage)
    accounts = URL('(?P<subsite>.*)fr/espace/devbavoirs.aspx\?mode=net&menu=cpte$', AccountsPage)
    fcpe_investment = URL(r'/fr/.*GoPositionsParFond.*',
                          r'/fr/espace/devbavoirs.aspx\?.*SituationParFonds.*GoOpenDetailFond.*',
                          r'(?P<subsite>.*)fr/espace/devbavoirs.aspx\?_tabi=C&a_mode=net&a_menu=cpte&_pid=SituationGlobale&_fid=GoPositionsParFond',
                          r'(?P<subsite>.*)fr/espace/devbavoirs.aspx\?_tabi=C&a_mode=net&a_menu=cpte&_pid=SituationParFonds.*', FCPEInvestmentPage)
    ccb_investment = URL('(?P<subsite>.*)fr/espace/devbavoirs.aspx\?_tabi=C&a_mode=net&a_menu=cpte&_pid=SituationGlobale&_fid=GoCCB', CCBInvestmentPage)
    history = URL('(?P<subsite>.*)fr/espace/devbavoirs.aspx\?mode=net&menu=cpte&page=operations',
                  '(?P<subsite>.*)fr/.*GoOperationsTraitees',
                  '(?P<subsite>.*)fr/.*GoOperationDetails', HistoryPage)

    def __init__(self, website, username, password, subsite="", *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.username = username
        self.password = password
        self.subsite = subsite

    def do_login(self):
        self.login.go()
        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        return self.accounts.go(subsite=self.subsite).iter_accounts()

    @need_login
    def iter_investment(self, account):
        fcpe_link = self.accounts.go(subsite=self.subsite).get_investment_link()
        ccb_link = self.accounts.go(subsite=self.subsite).get_pocket_link()

        if fcpe_link or ccb_link:
            return self._iter_investment(fcpe_link, ccb_link)
        else:
            return []

    def _iter_investment(self, fcpe_link, ccb_link):
        if fcpe_link:
            for inv in self.location(fcpe_link).page.iter_investment():
                yield inv

        if ccb_link:
            for inv in self.location(ccb_link).page.iter_investment():
                yield inv

    @need_login
    def iter_pocket(self, account):
        self.accounts.go(subsite=self.subsite)
        for inv in self.iter_investment(account):
            if inv._pocket_url:
                # Only FCPE investments have pocket link:
                self.location(inv._pocket_url)
                for pocket in self.page.iter_pocket(inv=inv):
                    yield pocket

        ccb_link = self.accounts.go(subsite=self.subsite).get_pocket_link()
        if ccb_link:
            for inv in self.location(ccb_link).page.iter_investment():
                for poc in self.page.iter_pocket(inv=inv):
                    yield poc

    @need_login
    def iter_history(self, account):
        link = self.history.go(subsite=self.subsite).get_link()
        if link:
            return self.location(link).page.iter_history()
        return iter([])

# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login

from .pages import (
    LoginPage, NewWebsitePage, AccountsPage, FCPEInvestmentPage,
    CCBInvestmentPage, HistoryPage, CustomPage, ActionNeededPage,
)


class CmesBrowser(LoginBrowser):
    BASEURL = 'https://www.cic-epargnesalariale.fr'

    login = URL('/espace-client/fr/identification/authentification.html', LoginPage)
    action_needed = URL('/espace-client/fr/epargnants/premiers-pas/saisir-vos-coordonnees/saisir-adresse-e-mail.html', ActionNeededPage)
    accounts = URL('(?P<subsite>.*)fr/espace/devbavoirs.aspx\?mode=net&menu=cpte$', AccountsPage)
    new_website = URL('(?P<subsite>.*)espace-client/fr/epargnants/tableau-de-bord/index.html', NewWebsitePage)
    fcpe_investment = URL(r'/fr/.*GoPositionsParFond.*',
                          r'/fr/espace/devbavoirs.aspx\?.*SituationParFonds.*GoOpenDetailFond.*',
                          r'(?P<subsite>.*)fr/espace/devbavoirs.aspx\?_tabi=(C|I1)&a_mode=net&a_menu=cpte&_pid=Situation(Globale|ParPlan)&_fid=GoPositionsParFond',
                          r'(?P<subsite>.*)fr/espace/devbavoirs.aspx\?_tabi=(C|I1)&a_mode=net&a_menu=cpte&_pid=SituationParFonds.*', FCPEInvestmentPage)
    ccb_investment = URL(r'(?P<subsite>.*)fr/espace/devbavoirs.aspx\?_tabi=C&a_mode=net&a_menu=cpte&_pid=SituationGlobale(&_fid=GoCCB|&k_support=CCB&_fid=GoPrint)', CCBInvestmentPage)
    history = URL('(?P<subsite>.*)fr/espace/devbavoirs.aspx\?mode=net&menu=cpte&page=operations',
                  '(?P<subsite>.*)fr/.*GoOperationsTraitees',
                  '(?P<subsite>.*)fr/.*GoOperationDetails', HistoryPage)
    custom_page = URL('/fr/espace/personnel/index.html', CustomPage)

    def __init__(self, username, password, website, subsite="", *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.username = username
        self.password = password
        self.subsite = subsite

    @property
    def logged(self):
        return 'IdSes' in self.session.cookies

    def do_login(self):
        self.login.go()
        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        self.accounts.go(subsite=self.subsite)

        if self.custom_page.is_here():
            # it can be redirected by accounts page, return on accounts page should be enough
            self.accounts.go(subsite=self.subsite)
            if self.custom_page.is_here():
                # Need to do it twice
                self.accounts.go(subsite=self.subsite)

        return self.page.iter_accounts()

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

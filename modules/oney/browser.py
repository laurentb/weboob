# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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

from datetime import date

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.tools.date import new_date

from .pages import (
    LoginPage, ClientPage, OperationsPage, ChoicePage,
    CreditHome, CreditAccountPage, CreditHistory, LastHistoryPage,
)

__all__ = ['OneyBrowser']


class OneyBrowser(LoginBrowser):
    BASEURL = 'https://www.oney.fr'

    login =       URL(r'/site/s/login/login.html', LoginPage)

    choice =      URL(r'/site/s/multimarque/choixsite.html', ChoicePage)
    choice_portal = URL(r'/site/s/login/loginidentifiant.html')

    client =      URL(r'/oney/client', ClientPage)
    operations =  URL(r'/oney/client', OperationsPage)
    card_page =   URL(r'/oney/client\?task=Synthese&process=SyntheseMultiCompte&indexSelectionne=(?P<acc_num>\d+)')

    credit_home = URL(r'/site/s/detailcompte/detailcompte.html', CreditHome)
    credit_info = URL(r'/site/s/detailcompte/ongletdetailcompte.html', CreditAccountPage)
    credit_hist = URL(r'/site/s/detailcompte/exportoperations.html', CreditHistory)
    last_hist =   URL(r'/site/s/detailcompte/ongletdernieresoperations.html', LastHistoryPage)

    has_oney = False
    has_other = False
    card_name = None

    def do_login(self):
        self.session.cookies.clear()

        self.login.go()

        self.page.login(self.username, self.password)

        if self.choice.is_here():
            self.has_other = self.has_oney = True
        elif self.credit_home.is_here():
            self.has_other = True
        elif self.client.is_here():
            self.has_oney = True
        else:
            raise BrowserIncorrectPassword()

    @need_login
    def go_site(self, site):
        if site == 'oney':
            if (
                self.credit_home.is_here() or self.credit_info.is_here()
                or self.credit_hist.is_here()
                or self.last_hist.is_here()
            ):

                self.choice.go()
                assert self.choice.is_here()
            if self.choice.is_here():
                self.choice_portal.go(data={'selectedSite': 'ONEY_HISTO'})

        elif site == 'other':
            if self.client.is_here() or self.operations.is_here():
                self.do_login()
                assert self.choice.is_here()
            if self.choice.is_here():
                self.choice_portal.go(data={'selectedSite': 'ONEY'})

    @need_login
    def get_accounts_list(self):
        accounts = []

        if self.has_other:
            self.go_site('other')
            self.credit_home.stay_or_go()
            self.card_name = self.page.get_name()
            self.credit_info.go()
            accounts.append(self.page.get_account())

        if self.has_oney:
            self.go_site('oney')
            self.client.stay_or_go()
            accounts.extend(self.page.iter_accounts())

        return accounts

    def _build_hist_form(self):
        form = {}
        d = date.today()
        form['jourDebut'] = '1'
        form['moisDebut'] = '1'
        form['anneeDebut'] = '2016'
        form['jourFin'] = str(d.day)
        form['moisFin'] = str(d.month)
        form['anneeFin'] = str(d.year)
        form['typeOpe'] = 'deux'
        form['formatFichier'] = 'xls' # or pdf... great choice
        return form

    @need_login
    def iter_history(self, account):
        self.go_site(account._site)
        if account._site == 'oney':
            if account._num:
                self.card_page.go(acc_num=account._num)
            post = {'task': 'Synthese', 'process': 'SyntheseCompte', 'taskid': 'Releve'}
            self.operations.go(data=post)

            for tr in self.page.iter_transactions(seen=set()):
                yield tr

        elif account._site == 'other':
            if self.last_hist.go().has_transactions():
                self.credit_hist.go(params=self._build_hist_form())
                d = date.today().replace(day=1) # TODO is it the right date?
                for tr in self.page.iter_history():
                    if new_date(tr.date) < d:
                        yield tr

    @need_login
    def iter_coming(self, account):
        self.go_site(account._site)
        if account._site == 'oney':
            if account._num:
                self.card_page.go(acc_num=account._num)
            post = {'task': 'OperationRecente', 'process': 'OperationRecente', 'taskid': 'OperationRecente'}
            self.operations.go(data=post)

            for tr in self.page.iter_transactions(seen=set()):
                yield tr

        elif account._site == 'other':
            if self.last_hist.go().has_transactions():
                self.credit_hist.go(params=self._build_hist_form())
                d = date.today().replace(day=1) # TODO is it the right date?
                for tr in self.page.iter_history():
                    if new_date(tr.date) >= d:
                        yield tr

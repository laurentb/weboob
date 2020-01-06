# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

from datetime import datetime

from dateutil.relativedelta import relativedelta
from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import  BrowserIncorrectPassword
from .pages import (
    LoginPage, AccountsPage, OperationsListPage, OperationPage, ActionNeededPage,
    InvestmentPage, InvestmentDetailsPage,
)


class CmesBrowser(LoginBrowser):
    BASEURL = 'https://www.cic-epargnesalariale.fr'

    login = URL(r'(?P<client_space>.*)fr/identification/authentification.html', LoginPage)

    action_needed = URL(
        r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/premiers-pas/saisir-vos-coordonnees.*',
        r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/conditions-generales-d-utilisation/index.html',
        ActionNeededPage
    )

    accounts = URL(
        r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/mon-epargne/situation-financiere-detaillee/index.html',
        r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/tableau-de-bord/index.html',
        AccountsPage
    )

    investments = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/supports/fiche-du-support.html', InvestmentPage)
    investment_details = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/supports/epargne-sur-le-support.html', InvestmentDetailsPage)

    operations_list = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/operations/index.html', OperationsListPage)

    operation = URL(r'(?P<subsite>.*)(?P<client_space>.*)fr/epargnants/operations/consulter-une-operation/index.html\?param_=(?P<idx>\d+)', OperationPage)

    client_space = 'espace-client/'

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
        self.login.go(client_space=self.client_space)
        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        self.accounts.go(subsite=self.subsite, client_space=self.client_space)
        return self.page.iter_accounts()

    @need_login
    def iter_investment(self, account):
        if 'compte courant bloqué' in account.label.lower():
            # CCB accounts have Pockets but no Investments
            return
        self.accounts.stay_or_go(subsite=self.subsite, client_space=self.client_space)
        for inv in self.page.iter_investments(account=account):
            if inv._url:
                # Go to the investment details to get employee savings attributes
                self.location(inv._url)

                # Fetch SRRI, asset category & recommended period
                self.page.fill_investment(obj=inv)

                performances = {}
                # Get 1-year performance
                url = self.page.get_form_url()
                self.location(url, data={'_FID_DoFilterChart_timePeriod:1Year': ''})
                performances[1] = self.page.get_performance()

                # Get 5-years performance
                url = self.page.get_form_url()
                self.location(url, data={'_FID_DoFilterChart_timePeriod:5Years': ''})
                performances[5] = self.page.get_performance()

                # There is no available form for 3-year history, we must build the request
                url = self.page.get_form_url()
                data = {
                    '[t:dbt%3adate;]Data_StartDate': (datetime.today() - relativedelta(years=3)).strftime('%d/%m/%Y'),
                    '[t:dbt%3adate;]Data_EndDate': datetime.today().strftime('%d/%m/%Y'),
                    '_FID_DoDateFilterChart': '',
                }
                self.location(url, data=data)
                performances[3] = self.page.get_performance()
                inv.performance_history = performances

                # Fetch investment quantity on the 'Mes Avoirs' tab
                self.page.go_investment_details()
                inv.quantity = self.page.get_quantity()
                self.page.go_back()

            else:
                self.logger.info('No available details for investment %s.', inv.label)
            yield inv

    @need_login
    def iter_history(self, account):
        self.operations_list.stay_or_go(subsite=self.subsite, client_space=self.client_space)
        for idx in self.page.get_operations_idx():
            self.operation.go(subsite=self.subsite, client_space=self.client_space, idx=idx)
            for tr in self.page.get_transactions():
                if account.label == tr._account_label:
                    yield tr

    @need_login
    def iter_pocket(self, account):
        self.accounts.stay_or_go(subsite=self.subsite, client_space=self.client_space)
        if 'compte courant bloqué' in account.label.lower():
            # CCB accounts have a specific table containing only Pockets
            for pocket in self.page.iter_ccb_pockets(account=account):
                yield pocket
        else:
            for inv in self.iter_investment(account=account):
                for pocket in self.page.iter_pocket(inv=inv):
                    yield pocket

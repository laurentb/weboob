# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from itertools import chain

from weboob.capabilities.bank import Account
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.tools.date import new_date

from .pages import (
    LoginPage, ClientPage, OperationsPage, ChoicePage,
    CreditHome, CreditAccountPage, CreditHistory, LastHistoryPage,
    ContextInitPage, SendUsernamePage, SendPasswordPage, CheckTokenPage,
)

__all__ = ['OneyBrowser']


class OneyBrowser(LoginBrowser):
    BASEURL = 'https://www.oney.fr'

    home_login = URL(
        r'/site/s/login/login.html',
        LoginPage
    )
    login = URL(
        r'https://login.oney.fr/login',
        r'https://login.oney.fr/context',
        LoginPage
    )

    send_username = URL(r'https://login.oney.fr/middle/authenticationflowinit', SendUsernamePage)
    send_password = URL(r'https://login.oney.fr/middle/completeauthflowstep', SendPasswordPage)
    context_init = URL(r'https://login.oney.fr/middle/context', ContextInitPage)

    check_token = URL(r'https://login.oney.fr/middle/check_token', CheckTokenPage)

    choice = URL(r'/site/s/multimarque/choixsite.html', ChoicePage)
    choice_portal = URL(r'/site/s/login/loginidentifiant.html')

    client = URL(r'/oney/client', ClientPage)
    operations = URL(r'/oney/client', OperationsPage)
    card_page = URL(r'/oney/client\?task=Synthese&process=SyntheseMultiCompte&indexSelectionne=(?P<acc_num>\d+)')

    credit_home = URL(r'/site/s/detailcompte/detailcompte.html', CreditHome)
    credit_info = URL(r'/site/s/detailcompte/ongletdetailcompte.html', CreditAccountPage)
    credit_hist = URL(r'/site/s/detailcompte/exportoperations.html', CreditHistory)
    last_hist = URL(r'/site/s/detailcompte/ongletdernieresoperations.html', LastHistoryPage)

    has_oney = False
    has_other = False
    card_name = None

    def do_login(self):
        self.session.cookies.clear()

        self.home_login.go(method="POST")
        context_token = self.page.get_context_token()
        assert context_token is not None, "Should not have context_token=None"

        self.context_init.go(params={'contextToken': context_token})
        success_url = self.page.get_success_url()
        customer_session_id = self.page.get_customer_session_id()

        self.session.headers.update({'Client-id': self.page.get_client_id()})

        # There is a VK on the website but it does not encode the password
        self.login.go()
        if '@' in self.username:
            auth_type = 'EML'
            step_type = 'EMAIL_PASSWORD'
        else:
            auth_type = 'IAD'
            step_type = 'IAD_ACCESS_CODE'

        self.send_username.go(json={
            'authentication_type': 'LIGHT',
            'authentication_factor': {
                'public_value': self.username,
                'type': auth_type,
            }
        })

        flow_id = self.page.get_flow_id()

        self.send_password.go(json={
            'flow_id': flow_id,
            'step_type': step_type,
            'value': self.password,
        })

        error = self.page.get_error()
        if error:
            raise BrowserIncorrectPassword(error)

        token = self.page.get_token()

        self.check_token.go(params={'token': token})
        self.location(success_url, params={
            'token': token,
            'customer_session_id': customer_session_id,
        })

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
            for acc_id in self.page.get_accounts_ids():
                self.credit_home.go(data={'numeroCompte': acc_id})
                label = self.page.get_label()
                if 'prêt' in label.lower():
                    acc = self.page.get_loan()
                else:
                    self.credit_info.go()
                    acc = self.page.get_account()
                    acc.label = label
                accounts.append(acc)

        if self.has_oney:
            self.go_site('oney')
            self.client.stay_or_go()
            accounts.extend(self.page.iter_accounts())

        return accounts

    def _build_hist_form(self, last_months=False):
        form = {}
        d = date.today()

        if not last_months:
            # before the last two months
            end = d.replace(day=1) + relativedelta(months=-1, days=-1)
            form['jourDebut'] = '1'
            form['moisDebut'] = '1'
            form['anneeDebut'] = '2016'
            form['jourFin'] = str(end.day)
            form['moisFin'] = str(end.month)
            form['anneeFin'] = str(end.year)
        else:
            # the last two months
            start = d.replace(day=1) - timedelta(days=1)
            form['jourDebut'] = '1'
            form['moisDebut'] = str(start.month)
            form['anneeDebut'] = str(start.year)
            form['jourFin'] = str(d.day)
            form['moisFin'] = str(d.month)
            form['anneeFin'] = str(d.year)

        form['typeOpe'] = 'deux'
        form['formatFichier'] = 'xls'  # or pdf... great choice
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

        elif account._site == 'other' and account.type != Account.TYPE_LOAN:
            self.credit_home.go(data={'numeroCompte': account.id})
            self.last_hist.go()
            if self.page.has_transactions():
                # transactions are missing from the xls from 2016 to today
                # so two requests are needed
                d = date.today()
                page_before = self.credit_hist.open(
                    params=self._build_hist_form(last_months=True)
                )
                page_today = self.credit_hist.go(
                    params=self._build_hist_form()
                )

                for tr in chain(page_before.iter_history(), page_today.iter_history()):
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

        elif account._site == 'other' and account.type != Account.TYPE_LOAN:
            self.credit_home.go(data={'numeroCompte': account.id})
            self.last_hist.go()
            if self.page.has_transactions():
                self.credit_hist.go(params=self._build_hist_form())
                d = date.today().replace(day=1)  # TODO is it the right date?
                for tr in self.page.iter_history():
                    if new_date(tr.date) >= d:
                        yield tr

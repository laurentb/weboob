# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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


from datetime import datetime

from dateutil.rrule import rrule, MONTHLY
from dateutil.relativedelta import relativedelta

from weboob.browser import LoginBrowser, need_login
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.url import URL

from .pages import (
    LoginPage, AuthPage, AccountsPage, AccountHistoryViewPage, AccountHistoryPage,
    ActionNeededPage, CardListPage,
    CardHistoryPage)


__all__ = ['BNPEnterprise']


class BNPEnterprise(LoginBrowser):
    BASEURL = 'https://secure1.entreprises.bnpparibas.net'

    login = URL('/sommaire/jsp/identification.jsp',
                '/sommaire/generateImg', LoginPage)
    auth = URL('/sommaire/PseMenuServlet', AuthPage)
    accounts = URL('/NCCPresentationWeb/e10_soldes/liste_soldes.do', AccountsPage)
    account_history_view = URL('/NCCPresentationWeb/e10_soldes/init.do\?nccIdSelected=NCC_Soldes',
                               '/NCCPresentationWeb/e11_releve_op/init.do\?identifiant=(?P<identifiant>)' + \
                               '&typeSolde=(?P<type_solde>)&typeReleve=(?P<type_releve>)&typeDate=(?P<type_date>)' + \
                               '&dateMin=(?P<date_min>)&dateMax=(?P<date_max>)&ajax=true',
                               '/NCCPresentationWeb/e11_releve_op/init.do', AccountHistoryViewPage)
    account_coming_view = URL('/NCCPresentationWeb/m04_selectionCompteGroupe/init.do\?type=compte&identifiant=(?P<identifiant>)', AccountHistoryViewPage)
    account_history = URL('/NCCPresentationWeb/e11_releve_op/listeOperations.do\?identifiant=(?P<identifiant>)' + \
                               '&dateMin=(?P<date_min>)&dateMax=(?P<date_max>)',
                          '/NCCPresentationWeb/e11_releve_op/listeOperations.do', AccountHistoryPage)
    account_coming = URL('/NCCPresentationWeb/e12_rep_cat_op/listOperations.do\?periode=date_valeur&identifiant=(?P<identifiant>)',
                         '/NCCPresentationWeb/e12_rep_cat_op/listOperations.do', AccountHistoryPage)

    card_init = URL(r'/NCCPresentationWeb/m04_selectionCompteGroupe/init.do\?type=compteCarte&identifiant=(?P<identifiant>)', CardListPage)
    card_init2 = URL(r'https://secure1.entreprises.bnpparibas.net/NCCPresentationWeb/e13_cartes/change_common.do', CardListPage)
    card_list = URL(r'/NCCPresentationWeb/e13_cartes/liste_cartes.do\?Ligne_Encour=', CardListPage)
    init_card_history = URL(r'/NCCPresentationWeb/e13_encours/init.do\?Id_Carte=(?P<card_id>)&Ligne_Encour=Global', CardHistoryPage)

    card_history = URL(r'/NCCPresentationWeb/e13_encours/liste_operations.do', CardHistoryPage)

    renew_pass = URL('/sommaire/PseRedirectPasswordConnect', ActionNeededPage)

    def __init__(self, *args, **kwargs):
        super(BNPEnterprise, self).__init__(*args, **kwargs)

        self.cache = {}
        self.cache['transactions'] = {}
        self.cache['coming_transactions'] = {}

    def do_login(self):
        self.login.go()

        if self.login.is_here() is False:
            return

        data = {}
        data['txtAuthentMode'] = 'PASSWORD'
        data['BEFORE_LOGIN_REQUEST'] = None
        data['txtPwdUserId'] = self.username
        data['gridpass_hidden_input'] = self.page.get_password(self.password)

        self.auth.go(data=data)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def get_accounts_list(self):
        if "accounts" not in self.cache.keys():
            accounts = []
            for account in self.accounts.stay_or_go().iter_accounts():
                accounts.append(account)
                if account._has_cards:
                    self.card_init.go(identifiant=account.iban)
                    self.card_init2.go()
                    self.card_list.go()
                    accounts.extend(self.page.iter_accounts(account_id=account.id, parent_iban=account.iban))

            self.cache['accounts'] = accounts
        return self.cache['accounts']

    @need_login
    def get_account(self, _id):
        for account in self.get_accounts_list():
            if account.id == _id:
                return account

    @need_login
    def iter_history(self, account):
        if account.id not in self.cache['transactions']:
            if account.type == Account.TYPE_CARD:
                return []
            else:
                dformat = "%Y%m%d"

                self.cache['transactions'][account.id] = []

                for date in rrule(MONTHLY, dtstart=(datetime.now() - relativedelta(months=3)), until=datetime.now()):
                    self.account_history_view.go(identifiant=account.iban, type_solde='C', type_releve='Comptable', \
                                                 type_date='O', date_min=(date + relativedelta(days=1)).strftime(dformat), \
                                                 date_max=(date + relativedelta(months=1)).strftime(dformat))
                    self.account_history.go(identifiant=account.iban, date_min=(date + relativedelta(days=1)).strftime(dformat), \
                                            date_max=(date + relativedelta(months=1)).strftime(dformat))

                    for transaction in [t for t in self.page.iter_history() if t._coming is False]:
                        self.cache['transactions'][account.id].append(transaction)
                self.cache['transactions'][account.id].sort(key=lambda t: t.date, reverse=True)

        return self.cache['transactions'][account.id]

    @need_login
    def iter_coming_operations(self, account):
        if account.id not in self.cache['coming_transactions']:
            if account.type == Account.TYPE_CARD:
                self.accounts.go()
                self.card_init.go(identifiant=account._parent_iban)
                self.card_init2.go()
                self.card_list.go()
                self.init_card_history.go(card_id=account._index)
                self.open('/NCCPresentationWeb/m99_pagination/setStatutPagination.do?ecran=e13_encours&nbEntreesParPage=TOUS&numPage=1')
                self.card_history.go()
            else:
                self.account_coming_view.go(identifiant=account.iban)
                self.account_coming.go(identifiant=account.iban)

            self.cache['coming_transactions'][account.id] = [t for t in self.page.iter_coming()]

        return self.cache['coming_transactions'][account.id]

    @need_login
    def iter_investment(self, account):
        raise NotImplementedError()

    @need_login
    def get_profile(self):
        profile = self.account_history_view.go().get_profile()
        if profile.name is NotAvailable:
            raise NotImplementedError

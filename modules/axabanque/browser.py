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


import json

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ClientError
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import BrowserIncorrectPassword

from .pages import KeyboardPage, LoginPage, PredisconnectedPage, BankAccountsPage, \
                   InvestmentActivatePage, InvestmentCguPage, InvestmentPage, \
                   CBTransactionsPage, TransactionsPage, UnavailablePage, IbanPage


class AXABanque(LoginBrowser):
    BASEURL = 'https://www.axabanque.fr/'

    # Login
    keyboard = URL('https://www.axa.fr/.sendvirtualkeyboard.json', KeyboardPage)
    login = URL('https://www.axa.fr/.loginAxa.json', LoginPage)
    predisconnected = URL('https://www.axa.fr/axa-predisconnect.html', PredisconnectedPage)
    # Bank
    bank_accounts = URL('transactionnel/client/liste-comptes.html',
                        'transactionnel/client/liste-(?P<tab>.*).html',
                        'webapp/axabanque/jsp/visionpatrimoniale/liste_panorama_.*\.faces',
                        'webapp/axabanque/client/sso/connexion\?token=(?P<token>.*)', BankAccountsPage)
    iban_pdf = URL('http://www.axabanque.fr/webapp/axabanque/formulaire_AXA_Banque/.*\.pdf.*', IbanPage)
    cbttransactions = URL('webapp/axabanque/jsp/detailCarteBleu.*.faces', CBTransactionsPage)
    transactions = URL('webapp/axabanque/jsp/panorama.faces',
                       'webapp/axabanque/jsp/visionpatrimoniale/panorama_.*\.faces',
                       'webapp/axabanque/jsp/detail.*.faces',
                       'webapp/axabanque/jsp/.*/detail.*.faces', TransactionsPage)
    unavailable = URL('login_errors/indisponibilite.*',
                      '.*page-indisponible.html.*',
                      '.*erreur/erreurBanque.faces', UnavailablePage)
    # Investment
    investment_activate = URL('https://client.axa.fr/_layouts/NOSI/MonitoringSedia.aspx', InvestmentActivatePage)
    investment_cgu = URL('https://client.axa.fr/_layouts/nosi/CGUPage.aspx', InvestmentCguPage)
    investment = URL('https://client.axa.fr/mes-comptes-et-contrats/Pages/(?P<page>.*)',
                     'https://client.axa.fr/_layouts/NOSI/LoadProfile.aspx',
                     'https://consultations.agipi.com', InvestmentPage)

    def __init__(self, *args, **kwargs):
        super(AXABanque, self).__init__(*args, **kwargs)
        self.tokens = {}
        # Need to cache every pages, website is too slow
        self.account_list = []
        self.investment_list = {}
        self.history_list = {}

    def do_login(self):
        html = json.loads(self.keyboard.go(data={'login': self.username}).content)['html']
        self.page.doc = self.page.build_doc(html.encode('utf-8'))

        data = self.page.get_data(self.username, self.password)
        error = self.login.go(data=data).check_error()

        # Activate tokens if there has
        if self.tokens['bank']:
            error = self.bank_accounts.go(token=self.tokens['bank']).check_error()
        if self.tokens['investment']:
            self.investment_activate.go(data={'tokenmixte': self.tokens['investment']})

        if error:
            raise BrowserIncorrectPassword(error)

    @need_login
    def iter_accounts(self):
        if not self.account_list:
            accounts = []
            # Get bank accounts if there has
            if self.tokens['bank']:
                self.transactions.go()
                self.bank_accounts.go()
                # Ugly 3 loops : nav through all tabs and pages
                for tab in self.page.get_tabs():
                    for page, page_args in self.bank_accounts.stay_or_go(tab=tab).get_pages(tab):
                        for a in page.get_list():
                            args = a._args
                            # Trying to get IBAN for checking accounts
                            if a.type == a.TYPE_CHECKING and 'paramCodeFamille' in args:
                                iban_params = {'action': 'RIBCC',
                                               'numCompte': args['paramNumCompte'],
                                               'codeFamille': args['paramCodeFamille'],
                                               'codeProduit': args['paramCodeProduit'],
                                               'codeSousProduit': args['paramCodeSousProduit'],
                                              }
                                try:
                                    r = self.open('/webapp/axabanque/popupPDF', params=iban_params)
                                    a.iban = r.page.get_iban()
                                except ClientError:
                                    a.iban = NotAvailable
                            # Need it to get accounts from tabs
                            a._tab, a._pargs, a._purl = tab, page_args, self.url
                            accounts.append(a)
            # Get investment accounts if there has
            if self.tokens['investment']:
                self.investment_pages = []
                self.investment.go(page="default.aspx").get_home()
                self.investment.go(page="default.aspx")
                # If user has cgu
                if not self.investment_cgu.is_here():
                    for form in self.page.get_forms():
                        for a in self.investment.go(page="PartialUpdatePanelLoader.ashx", \
                                data=form).iter_accounts():
                            accounts.append(a)
            self.account_list = accounts
        return iter(self.account_list)

    @need_login
    def go_account_pages(self, account, action):
        # Default to "comptes"
        tab = "comptes" if not hasattr(account, '_tab') else account._tab
        self.bank_accounts.go(tab=tab)
        args = account._args
        args['javax.faces.ViewState'] = self.page.get_view_state()
        # Nav for accounts in tab pages
        if tab != "comptes" and hasattr(account, '_url') \
                and hasattr(account, '_purl') and hasattr(account, '_pargs'):
            self.location(account._purl, data=account._pargs)
            self.location(account._url, data=args)
            # Check if we are on the good tab
            if isinstance(self.page, TransactionsPage):
                self.page.go_action(action)
        else:
            self.transactions.go(data=args)

    @need_login
    def iter_investment(self, account):
        if account.id not in self.investment_list:
            invs = []
            # Side investment's website
            if account._acctype is "investment":
                invs = [i for i in account._page.iter_investment()]
            # Main website with investments
            elif account._acctype is "bank" and account._hasinv:
                self.go_account_pages(account, "investment")
                invs = [i for i in self.page.iter_investment()]
            self.investment_list[account.id] = invs
        return iter(self.investment_list[account.id])

    @need_login
    def iter_history(self, account):
        if account.id not in self.history_list:
            trs = []
            # Side investment's website
            if account._acctype is "investment":
                self.accform = account._accform
                trs = [a for a in account._page.iter_history()]
            # Main website withouth investments
            elif account._acctype is "bank" and not account._hasinv:
                self.go_account_pages(account, "history")
                if self.page.more_history():
                    trs = [a for a in self.page.get_history()]
            self.history_list[account.id] = trs
        return iter(self.history_list[account.id])

# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


import re

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import NotAvailable

from .pages import LoginPage, Login2Page, IndexPage, AccountsPage, IbanPage, IbanPDFPage, TransactionsPage, \
                   CardPage, ValuationPage, LoanPage, MarketPage, AssurancePage, LogoutPage


class Barclays(LoginBrowser):
    BASEURL = 'https://www.barclays.fr'

    index = URL('https?://.*.barclays.fr/\d-index.html',                                 IndexPage)
    login = URL('https://.*.barclays.fr/barclaysnetV2/logininstit.do.*',                 LoginPage)
    login2 = URL('https://.*.barclays.fr/barclaysnetV2/loginSecurite.do.*',              Login2Page)
    logout = URL('https://.*.barclays.fr/bayexterne/barclaysnet/deconnexion/index.html', LogoutPage)
    accounts = URL('https://.*.barclays.fr/barclaysnetV2/tbord.do.*',                    AccountsPage)
    iban = URL('https://.*.barclays.fr/barclaysnetV2/editionRIB.do.*',                   IbanPage)
    ibanpdf = URL('https://.*.barclays.fr/barclaysnetV2/telechargerRIB.pdf',             IbanPDFPage)
    transactions = URL('https://.*.barclays.fr/barclaysnetV2/releve.do.*',               TransactionsPage)
    card = URL('https://.*.barclays.fr/barclaysnetV2/cartes.do.*',                       CardPage)
    valuation = URL('https://.*.barclays.fr/barclaysnetV2/valuationViewBank.do.*',       ValuationPage)
    loan = URL('https://.*.barclays.fr/barclaysnetV2/pret.do.*',
               'https://.*.barclays.fr/barclaysnetV2/revolving.do.*',
               LoanPage)
    market = URL('https://.*.barclays.fr/barclaysnetV2/titre.do.*',                      MarketPage)
    assurance = URL('https://.*.barclays.fr/barclaysnetV2/assurance.do.*',
                    'https://.*.barclays.fr/barclaysnetV2/assuranceSupports.do.*',       AssurancePage)

    SESSION_PARAM = None

    def __init__(self, secret, *args, **kwargs):
        super(Barclays, self).__init__(*args, **kwargs)
        self.secret = secret
        self.cache = {}

    def is_logged(self):
        return self.page is not None and not (self.login.is_here() or self.index.is_here() or self.login2.is_here())

    def go_home(self):
        if self.is_logged():
            link = self.page.doc.xpath('.//a[contains(@id, "tbordalllink")]')[0].attrib['href']
            m = re.match('(.*?fr)', self.url)
            if m:
                absurl = m.group(1)
                self.location('%s%s' % (absurl, link))
        else:
            self.do_login()

    def set_session_param(self):
        if self.is_logged():
            link = self.page.doc.xpath('.//a[contains(@id, "tbordalllink")]')[0].attrib['href']
            m = re.search('&(.*)', link)
            if m:
                self.SESSION_PARAM = m.group(1)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if self.is_logged():
            return

        if not self.login.is_here():
            self.location('https://b-net.barclays.fr/barclaysnetV2/logininstit.do?lang=fr&nodoctype=0')

        self.page.login(self.username, self.password)

        if not self.page.has_redirect():
            raise BrowserIncorrectPassword()

        self.location('loginSecurite.do')

        if self.logout.is_here():
            raise BrowserIncorrectPassword()

        self.page.login(self.secret)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

        self.set_session_param()

    def get_ibans_form(self):
        link = self.page.get_ibanlink()
        if link:
            self.location(link.split('/')[-1])
            return self.page.get_list()
        return False

    @need_login
    def get_accounts_list(self):
        if 'accs' not in self.cache.keys():
            if not self.accounts.is_here():
                self.go_home()
            accounts = self.page.get_list()
            accounts_url = self.url
            ibans = self.get_ibans_form()
            accs = []
            for a in accounts:
                if ibans and a.id in ibans['list']:
                    ibans['form']['checkaccount'] = ibans['list'][a.id]
                    if ibans['form'].req:
                        # this form has been submitted and whe have to rebuild data
                        ibans['form'].req.data['checkaccount'] = ibans['list'][a.id]
                    ibans['form'].submit()
                    a.iban = self.page.get_iban()
                else:
                    a.iban = NotAvailable
                accs.append(a)
            self.location(accounts_url)
            self.cache['accs'] = accs
        return self.cache['accs']

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_related_account(self, related_accid):
        l = []
        for a in self.get_accounts_list():
            if related_accid in a.id and a.type == a.TYPE_CHECKING:
                l.append(a)
        assert len(l) == 1
        return l[0]

    @need_login
    def get_history(self, account):
        if not self.accounts.is_here():
            self.go_home()

        self.location(account._link)

        assert (self.transactions.is_here() or self.valuation.is_here() or self.loan.is_here() \
                or self.market.is_here() or self.assurance.is_here() or self.card.is_here())

        transactions = list()
        while True:
            for tr in self.page.get_history():
                transactions.append(tr)
            next_page = self.page.get_next_page()
            if next_page:
                self.location(next_page)
            else:
                break

        if account._attached_acc is not None:
            for tr in self.get_history(self.get_related_account(account._attached_acc)):
                if (tr.raw.startswith('ACHAT CARTE -DEBIT DIFFERE') or 'ACHAT-DEBIT DIFFERE' in tr.raw) and account.id[:6] in tr.raw and account.id[:4] in tr.raw:
                    tr.amount *= -1
                    transactions.append(tr)

        for tr in sorted(transactions, key=lambda t: t.rdate, reverse=True) :
            yield tr

    @need_login
    def iter_investments(self, account):
        if account.type not in (account.TYPE_MARKET, account.TYPE_LIFE_INSURANCE):
            raise NotImplementedError()

        if not self.accounts.is_here():
            self.go_home()

        self.location(account._link)

        if account.type == account.TYPE_LIFE_INSURANCE:
            self.location(self.url.replace('assurance.do', 'assuranceSupports.do'))

        return self.page.iter_investments()

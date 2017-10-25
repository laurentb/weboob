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

from .pages import (
    LoginPage, AccountsPage, AMFHSBCPage, AMFAmundiPage, AMFSGPage, HistoryPage,
    ErrorPage, LyxorfcpePage, EcofiPage, EcofiDummyPage,
)


class S2eBrowser(LoginBrowser):
    login = URL('/portal/salarie-(?P<slug>\w+)/authentification',
                '/portal/j_security_check', LoginPage)
    accounts = URL('/portal/salarie-(?P<slug>\w+)/monepargne/mesavoirs\?language=(?P<lang>)',
                   '/portal/salarie-(?P<slug>\w+)/monepargne/mesavoirs', AccountsPage)
    amfcode_hsbc = URL('https://www.assetmanagement.hsbc.com/feedRequest', AMFHSBCPage)
    amfcode_amundi = URL('https://www.amundi-ee.com/entr/product', AMFAmundiPage)
    amfcode_sg = URL('http://sggestion-ede.com/product', AMFSGPage)
    isincode_ecofi = URL(r'http://www.ecofi.fr/fr/fonds/.*#yes\?bypass=clientprive', EcofiPage)
    pdf_file_ecofi = URL(r'http://www.ecofi.fr/sites/.*', EcofiDummyPage)
    lyxorfcpe = URL('http://www.lyxorfcpe.com/part', LyxorfcpePage)
    history = URL('/portal/salarie-(?P<slug>\w+)/operations/consulteroperations', HistoryPage)
    error = URL('/maintenance/HSBC/', ErrorPage)

    def __init__(self, *args, **kwargs):
        self.secret = None
        if 'secret' in kwargs:
            self.secret = kwargs['secret']
            del kwargs['secret']
        super(S2eBrowser, self).__init__(*args, **kwargs)
        self.cache = {}
        self.cache['invs'] = {}
        self.cache['pockets'] = {}
        self.cache['details'] = {}

    def do_login(self):
        self.login.go(slug=self.SLUG).login(self.username, self.password, self.secret)

        if self.login.is_here():
            error = self.page.get_error()
            raise BrowserIncorrectPassword(error)

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            self.accounts.stay_or_go(slug=self.SLUG, lang=self.LANG)
            # weird wrongpass
            if not self.accounts.is_here():
                raise BrowserIncorrectPassword()
            multi = self.page.get_multi()
            if len(multi):
                # Handle multi entreprise accounts
                accs = []
                for id in multi:
                    self.page.go_multi(id)
                    for a in self.accounts.go(slug=self.SLUG).iter_accounts():
                        a._multi = id
                        accs.append(a)
            else:
                accs = [a for a in self.page.iter_accounts()]
            self.cache['accs'] = accs
        return self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            self.accounts.stay_or_go(slug=self.SLUG)
            # Handle multi entreprise accounts
            if hasattr(account, '_multi'):
                self.page.go_multi(account._multi)
                self.accounts.go(slug=self.SLUG)
            # Select account
            self.page.get_investment_pages(account.id)
            invs = [i for i in self.page.iter_investment()]
            # Get page with quantity
            self.page.get_investment_pages(account.id, valuation=False)
            self.cache['invs'][account.id] = self.page.update_invs_quantity(invs)
        return self.cache['invs'][account.id]

    @need_login
    def iter_pocket(self, account):
        if account.id not in self.cache['pockets']:
            self.iter_investment(account)
            # Select account
            self.page.get_investment_pages(account.id, pocket=True)
            pockets = [p for p in self.page.iter_pocket(accid=account.id)]
            # Get page with quantity
            self.page.get_investment_pages(account.id, valuation=False, pocket=True)
            self.cache['pockets'][account.id] = self.page.update_pockets_quantity(pockets)
        return self.cache['pockets'][account.id]

    @need_login
    def iter_history(self, account):
        self.history.stay_or_go(slug=self.SLUG)
        # Handle multi entreprise accounts
        if hasattr(account, '_multi'):
            self.page.go_multi(account._multi)
            self.history.go(slug=self.SLUG)
        # Get more transactions on each page
        self.page.show_more("50")
        for tr in self.page.iter_history(accid=account.id):
            yield tr
        # Go back to first page
        self.page.go_start()


class EsaliaBrowser(S2eBrowser):
    BASEURL = 'https://salaries.esalia.com'
    SLUG = 'sg'
    LANG = 'fr' # ['fr', 'en']


class CapeasiBrowser(S2eBrowser):
    BASEURL = 'https://www.capeasi.com'
    SLUG = 'axa'
    LANG = 'fr' # ['fr', 'en']


class ErehsbcBrowser(S2eBrowser):
    BASEURL = 'https://epargnant.ere.hsbc.fr'
    SLUG = 'hsbc'
    LANG = 'fr' # ['fr', 'en']


class BnppereBrowser(S2eBrowser):
    BASEURL = 'https://personeo.epargne-retraite-entreprises.bnpparibas.com'
    SLUG = 'bnp'
    LANG = 'fr' # ['fr', 'en']

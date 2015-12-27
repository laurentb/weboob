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


import urllib

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrokenPageError
from weboob.deprecated.browser.parsers.iparser import RawParser

from .pages import LoginPage, IndexPage, AccountsPage, AccountsFullPage, CardsPage, TransactionsPage, \
                   UnavailablePage, RedirectPage, HomePage, Login2Page, ErrorPage, \
                   LineboursePage, NatixisPage, InvestmentNatixisPage, InvestmentLineboursePage, MessagePage, \
                   DocumentsPage, PostDocument, ExtractPdf


__all__ = ['BanquePopulaire']


class BanquePopulaire(Browser):
    PROTOCOL = 'https'
    ENCODING = 'iso-8859-15'
    PAGES = {'https://[^/]+/auth/UI/Login.*':                                                   LoginPage,
             'https://[^/]+/cyber/internet/Login.do':                                           IndexPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=mesComptes.*':             AccountsPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=maSyntheseGratuite.*':     AccountsPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=accueilSynthese.*':        AccountsPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=equipementComplet.*':      AccountsPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=documentsDemat.*':           DocumentsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=EQUIPEMENT_COMPLET.*': AccountsFullPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=VUE_COMPLETE.*': AccountsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=ENCOURS_COMPTE.*': CardsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=SELECTION_ENCOURS_CARTE.*':   TransactionsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=SOLDE.*':   TransactionsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=CONTRAT.*':   TransactionsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=TELECHARGER.*':   PostDocument,
             'https://[^/]+/cyber/internet/Page.do\?.*':                                        TransactionsPage,
             'https://[^/]+/cyber/internet/Sort.do\?.*':                                        TransactionsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do':                                    ErrorPage,
             'https://[^/]+/cyber/internet/DownloadDocument.do\?documentId=.*':                 (ExtractPdf, RawParser()),
             'https://[^/]+/s3f-web/.*':                                                        UnavailablePage,
             'https://[^/]+/static/errors/nondispo.html':                                       UnavailablePage,
             'https://[^/]+/portailinternet/_layouts/Ibp.Cyi.Layouts/RedirectSegment.aspx.*':   RedirectPage,
             'https://[^/]+/portailinternet/Catalogue/Segments/.*.aspx(\?vary=(?P<vary>.*))?':  HomePage,
             'https://[^/]+/portailinternet/Pages/.*.aspx\?vary=(?P<vary>.*)':                  HomePage,
             'https://[^/]+/portailinternet/Pages/default.aspx':                                HomePage,
             'https://[^/]+/portailinternet/Transactionnel/Pages/CyberIntegrationPage.aspx':    HomePage,
             'https://[^/]+/WebSSO_BP/_(?P<bankid>\d+)/index.html\?transactionID=(?P<transactionID>.*)': Login2Page,
             'https://www.linebourse.fr/ReroutageSJR':                                          LineboursePage,
             'https://www.linebourse.fr/DetailMessage.*':                                       MessagePage,
             'https://www.linebourse.fr/Portefeuille':                                          InvestmentLineboursePage,
             'https://www.assurances.natixis.fr/espaceinternet-bp/views/common.*':              NatixisPage,
             'https://www.assurances.natixis.fr/espaceinternet-bp/views/contrat.*':             InvestmentNatixisPage,
            }

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        self.token = None

        Browser.__init__(self, *args, **kwargs)

    # XXX FUCKING HACK BECAUSE BANQUE POPULAIRE ARE FAGGOTS AND INCLUDE NULL
    # BYTES IN DOCUMENTS.
    def get_document(self, result, parser=None, encoding=None):
        from io import BytesIO
        buf = BytesIO(result.read().replace('\0', ''))
        return Browser.get_document(self, buf, parser, encoding)

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def home(self):
        self.login()

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('%s://%s' % (self.PROTOCOL, self.DOMAIN), no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    ACCOUNT_URLS = ['mesComptes', 'mesComptesPRO', 'maSyntheseGratuite', 'accueilSynthese', 'equipementComplet']

    def go_on_accounts_list(self):
        for taskInfoOID in self.ACCOUNT_URLS:
            self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID=taskInfoOID, token=self.token))
            if not self.page.is_error():
                if self.page.pop_up():
                    self.logger.debug('Popup displayed, retry')
                    self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID=taskInfoOID, token=self.token))
                self.ACCOUNT_URLS = [taskInfoOID]
                break
        else:
            raise BrokenPageError('Unable to go on the accounts list page')

        if self.page.is_short_list():
            self.select_form(nr=0)
            self.set_all_readonly(False)
            self['dialogActionPerformed'] = 'EQUIPEMENT_COMPLET'
            self['token'] = self.page.build_token(self['token'])
            self.submit()

    def get_accounts_list(self, get_iban=True):
        # We have to parse account list in 2 different way depending if we want the iban number or not
        # thanks to stateful website
        self.go_on_accounts_list()

        next_pages = []
        accounts = []

        for a in self.page.iter_accounts(next_pages):
            if get_iban:
                accounts.append(a)
            else:
                yield a

        while len(next_pages) > 0:
            next_page = next_pages.pop()

            if not self.is_on_page(AccountsFullPage):
                self.go_on_accounts_list()
            # If there is an action needed to go to the "next page", do it.
            if 'prevAction' in next_page:
                params = self.page.get_params()
                params['dialogActionPerformed'] = next_page.pop('prevAction')
                params['token'] = self.page.build_token(self.token)
                self.location('/cyber/internet/ContinueTask.do', urllib.urlencode(params))

            next_page['token'] = self.page.build_token(self.token)
            self.location('/cyber/internet/ContinueTask.do', urllib.urlencode(next_page))

            for a in self.page.iter_accounts(next_pages):
                if get_iban:
                    accounts.append(a)
                else:
                    yield a

        if get_iban:
            for a in accounts:
                iban = self.get_iban_number(a)
                if iban:
                    a.iban = iban
                yield a



    def get_iban_number(self, account):
        self.location('/cyber/internet/StartTask.do?taskInfoOID=documentsDemat&token=%s' % self.page.build_token(self.token))
        token = self.page.build_token(self.token)
        #We need to get an extract document because we can find iban number on it
        if self.is_on_page(DocumentsPage):
            doc_id = self.page.get_account_extract(account.id)
            if doc_id:
                id = self.page.get_doc_id()
                if id:
                    self.location('/cyber/internet/DownloadDocument.do?documentId=%s' % id)
                    if self.is_on_page(ExtractPdf):
                        iban = self.page.get_iban()
                        self.location('/cyber/internet/StartTask.do?taskInfoOID=documentsDemat&token=%s' % token)
                        return iban
        return None


    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list(False):
            if a.id == id:
                return a

        return None

    def get_history(self, account, coming=False):
        account = self.get_account(account.id)

        if coming:
            params = account._coming_params
        else:
            params = account._params

        if params is None:
            return

        params['token'] = self.page.build_token(params['token'])

        self.location('/cyber/internet/ContinueTask.do', urllib.urlencode(params))

        if not self.page or self.page.no_operations():
            return

        # Sort by values dates (see comment in TransactionsPage.get_history)
        if len(self.page.document.xpath('//a[@id="tcl4_srt"]')) > 0:
            self.select_form(predicate=lambda form: form.attrs.get('id', '') == 'myForm')
            self.form.action = self.absurl('/cyber/internet/Sort.do?property=tbl1&sortBlocId=blc2&columnName=dateValeur')
            params['token'] = self.page.build_token(params['token'])
            self.submit()

        while True:
            assert self.is_on_page(TransactionsPage)

            for tr in self.page.get_history(account, coming):
                yield tr

            next_params = self.page.get_next_params()
            if next_params is None:
                return

            self.location(self.buildurl('/cyber/internet/Page.do', **next_params))

    def get_investment(self, account):
        if not account._invest_params:
            raise NotImplementedError()

        account = self.get_account(account.id)
        params = account._invest_params
        params['token'] = self.page.build_token(params['token'])
        self.location('/cyber/internet/ContinueTask.do', urllib.urlencode(params))

        if self.is_on_page(ErrorPage):
            raise NotImplementedError()

        url, params = self.page.get_investment_page_params()
        if params:
            self.location(url, urllib.urlencode(params))
            if self.is_on_page(LineboursePage):
                self.location('https://www.linebourse.fr/Portefeuille')
                while self.is_on_page(MessagePage):
                    self.page.skip()
                    self.location('https://www.linebourse.fr/Portefeuille')
            elif self.is_on_page(NatixisPage):
                self.page.submit_form()
            return self.page.get_investments()

        return iter([])

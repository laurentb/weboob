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

from __future__ import unicode_literals

import re

from collections import OrderedDict
from functools import wraps

from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.browser.exceptions import HTTPNotFound, ServerError
from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable, find_object
from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .pages import (
    LoggedOut,
    LoginPage, IndexPage, AccountsPage, AccountsFullPage, CardsPage, TransactionsPage,
    UnavailablePage, RedirectPage, HomePage, Login2Page, ErrorPage,
    IbanPage, AdvisorPage, TransactionDetailPage, TransactionsBackPage,
    NatixisPage, EtnaPage, NatixisInvestPage, NatixisHistoryPage, NatixisErrorPage,
    NatixisDetailsPage, NatixisChoicePage, NatixisRedirect,
    LineboursePage, AlreadyLoginPage,
)

from .linebourse_browser import LinebourseBrowser


__all__ = ['BanquePopulaire']


class BrokenPageError(Exception):
    pass


def retry(exc_check, tries=4):
    """Decorate a function to retry several times in case of exception.

    The decorated function is called at max 4 times. It is retried only when it
    raises an exception of the type `exc_check`.
    If the function call succeeds and returns an iterator, a wrapper to the
    iterator is returned. If iterating on the result raises an exception of type
    `exc_check`, the iterator is recreated by re-calling the function, but the
    values already yielded will not be re-yielded.
    For consistency, the function MUST always return values in the same order.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(browser, *args, **kwargs):
            cb = lambda: func(browser, *args, **kwargs)

            for i in range(tries, 0, -1):
                try:
                    ret = cb()
                except exc_check as exc:
                    browser.logger.debug('%s raised, retrying', exc)
                    continue

                if not (hasattr(ret, '__next__') or hasattr(ret, 'next')):
                    return ret  # simple value, no need to retry on items
                return iter_retry(cb, value=ret, remaining=i, exc_check=exc_check, logger=browser.logger)

            raise BrowserUnavailable('Site did not reply successfully after multiple tries')

        return wrapper
    return decorator


def no_need_login(func):
    # indicate a login is in progress, so LoggedOut should not be raised
    def wrapper(browser, *args, **kwargs):
        browser.no_login += 1
        try:
            return func(browser, *args, **kwargs)
        finally:
            browser.no_login -= 1

    return wrapper


class BanquePopulaire(LoginBrowser):
    login_page = URL(r'https://[^/]+/auth/UI/Login.*', LoginPage)
    index_page = URL(r'https://[^/]+/cyber/internet/Login.do', IndexPage)
    accounts_page = URL(r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=mesComptes.*',
                        r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=maSyntheseGratuite.*',
                        r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=accueilSynthese.*',
                        r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=equipementComplet.*',
                        r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=VUE_COMPLETE.*',
                        AccountsPage)

    iban_page = URL(r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=cyberIBAN.*',
                    r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=DETAIL_IBAN_RIB.*',
                    IbanPage)

    accounts_full_page = URL(r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=EQUIPEMENT_COMPLET.*',
                             AccountsFullPage)

    cards_page = URL(r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=ENCOURS_COMPTE.*', CardsPage)

    transactions_page = URL(r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=SELECTION_ENCOURS_CARTE.*',
                            r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=SOLDE.*',
                            r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=CONTRAT.*',
                            r'https://[^/]+/cyber/internet/ContinueTask.do\?.*ConsultationDetail.*ActionPerformed=BACK.*',
                            r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=ordreBourseCTJ.*',
                            r'https://[^/]+/cyber/internet/Page.do\?.*',
                            r'https://[^/]+/cyber/internet/Sort.do\?.*',
                            TransactionsPage)

    transactions_back_page = URL(r'https://[^/]+/cyber/internet/ContinueTask.do\?.*ActionPerformed=BACK.*', TransactionsBackPage)

    transaction_detail_page = URL(r'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=DETAIL_ECRITURE.*', TransactionDetailPage)

    error_page = URL(r'https://[^/]+/cyber/internet/ContinueTask.do',
                     r'https://[^/]+/_layouts/error.aspx',
                     r'https://[^/]+/portailinternet/_layouts/Ibp.Cyi.Administration/RedirectPageError.aspx',
                     ErrorPage)

    unavailable_page = URL(r'https://[^/]+/s3f-web/.*',
                           r'https://[^/]+/static/errors/nondispo.html',
                           r'/i-RIA/swc/1.0.0/desktop/index.html',
                           UnavailablePage)

    redirect_page = URL(r'https://[^/]+/portailinternet/_layouts/Ibp.Cyi.Layouts/RedirectSegment.aspx.*', RedirectPage)
    home_page = URL(r'https://[^/]+/portailinternet/Catalogue/Segments/.*.aspx(\?vary=(?P<vary>.*))?',
                    r'https://[^/]+/portailinternet/Pages/.*.aspx\?vary=(?P<vary>.*)',
                    r'https://[^/]+/portailinternet/Pages/[dD]efault.aspx',
                    r'https://[^/]+/portailinternet/Transactionnel/Pages/CyberIntegrationPage.aspx',
                    r'https://[^/]+/cyber/internet/ShowPortal.do\?token=.*',
                    HomePage)

    already_login_page = URL(r'https://[^/]+/dacswebssoissuer.*',
                             r'https://[^/]+/WebSSO_BP/_(?P<bankid>\d+)/index.html\?transactionID=(?P<transactionID>.*)', AlreadyLoginPage)
    login2_page = URL(r'https://[^/]+/WebSSO_BP/_(?P<bankid>\d+)/index.html\?transactionID=(?P<transactionID>.*)', Login2Page)

    # natixis
    natixis_redirect = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/views/common/routage.xhtml.*?windowId=[a-f0-9]+$', NatixisRedirect)
    natixis_choice = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/views/contrat/list.xhtml\?.*', NatixisChoicePage)
    natixis_page = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/views/common.*', NatixisPage)
    etna = URL(r'https://www.assurances.natixis.fr/etna-ihs-bp/#/contratVie/(?P<id1>\w+)/(?P<id2>\w+)/(?P<id3>\w+).*',
               r'https://www.assurances.natixis.fr/espaceinternet-bp/views/contrat/detail/vie/view.xhtml\?windowId=.*&reference=(?P<id3>\d+)&codeSociete=(?P<id1>[^&]*)&codeProduit=(?P<id2>[^&]*).*',
               EtnaPage)
    natixis_error_page = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/error-redirect.*',
                             r'https://www.assurances.natixis.fr/etna-ihs-bp/#/equipement;codeEtab=.*\?windowId=.*',
                             NatixisErrorPage)
    natixis_invest = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/rest/v2/contratVie/load/(?P<id1>\w+)/(?P<id2>\w+)/(?P<id3>\w+)', NatixisInvestPage)
    natixis_history = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/rest/v2/contratVie/load-operation/(?P<id1>\w+)/(?P<id2>\w+)/(?P<id3>\w+)', NatixisHistoryPage)
    natixis_pdf = URL(r'https://www.assurances.natixis.fr/espaceinternet-bp/rest/v2/contratVie/load-releve/(?P<id1>\w+)/(?P<id2>\w+)/(?P<id3>\w+)/(?P<year>\d+)', NatixisDetailsPage)

    linebourse_home = URL(r'https://www.linebourse.fr/ReroutageSJR', LineboursePage)

    advisor = URL(r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=accueil.*',
                  r'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=contacter.*', AdvisorPage)

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'https://%s' % website
        # this url is required because the creditmaritime abstract uses an other url
        if 'cmgo.creditmaritime' in self.BASEURL:
            self.redirect_url = 'https://www.icgauth.creditmaritime.groupe.banquepopulaire.fr/dacsrest/api/v1u0/transaction/'
        else:
            self.redirect_url = 'https://www.icgauth.banquepopulaire.fr/dacsrest/api/v1u0/transaction/'
        self.token = None
        self.weboob = kwargs['weboob']
        super(BanquePopulaire, self).__init__(*args, **kwargs)

        dirname = self.responses_dirname
        if dirname:
            dirname += '/bourse'
        self.linebourse = LinebourseBrowser('https://www.linebourse.fr', logger=self.logger, responses_dirname=dirname, weboob=self.weboob, proxy=self.PROXIES)

        self.investments = {}

    def deinit(self):
        super(BanquePopulaire, self).deinit()
        self.linebourse.deinit()

    no_login = 0

    @no_need_login
    def do_login(self):
        self.location(self.BASEURL)
        # avoids trying to relog in while it's already on home page
        if self.home_page.is_here():
            return
        self.page.login(self.username, self.password)
        if self.login_page.is_here():
            raise BrowserIncorrectPassword()

    ACCOUNT_URLS = ['mesComptes', 'mesComptesPRO', 'maSyntheseGratuite', 'accueilSynthese', 'equipementComplet']

    @retry(BrokenPageError)
    @need_login
    def go_on_accounts_list(self):
        for taskInfoOID in self.ACCOUNT_URLS:
            data = OrderedDict([('taskInfoOID', taskInfoOID), ('token', self.token)])
            self.location(self.absurl('/cyber/internet/StartTask.do', base=True), params=data)
            if not self.page.is_error():
                if self.page.pop_up():
                    self.logger.debug('Popup displayed, retry')
                    data = OrderedDict([('taskInfoOID', taskInfoOID), ('token', self.token)])
                    self.location('/cyber/internet/StartTask.do', params=data)
                self.ACCOUNT_URLS = [taskInfoOID]
                break
        else:
            raise BrokenPageError('Unable to go on the accounts list page')

        if self.page.is_short_list():
            form = self.page.get_form(nr=0)
            form['dialogActionPerformed'] = 'EQUIPEMENT_COMPLET'
            form['token'] = self.page.build_token(form['token'])
            form.submit()

    @retry(LoggedOut)
    @need_login
    def get_accounts_list(self, get_iban=True):
        # We have to parse account list in 2 different way depending if we want the iban number or not
        # thanks to stateful website
        self.go_on_accounts_list()

        next_pages = []
        accounts = []

        for a in self.page.iter_accounts(next_pages):
            accounts.append(a)
            if not get_iban:
                yield a

        while len(next_pages) > 0:
            next_page = next_pages.pop()

            if not self.accounts_full_page.is_here():
                self.go_on_accounts_list()
            # If there is an action needed to go to the "next page", do it.
            if 'prevAction' in next_page:
                params = self.page.get_params()
                params['dialogActionPerformed'] = next_page.pop('prevAction')
                params['token'] = self.page.build_token(self.token)
                self.location('/cyber/internet/ContinueTask.do', data=params)

            next_page['token'] = self.page.build_token(self.token)
            self.location('/cyber/internet/ContinueTask.do', data=next_page)

            for a in self.page.iter_accounts(next_pages):
                accounts.append(a)
                if not get_iban:
                    yield a

        if get_iban:
            for a in accounts:
                a.iban = self.get_iban_number(a)
            for a in accounts:
                self.get_investment(a)
                yield a

    @need_login
    def get_iban_number(self, account):
        url = self.absurl('/cyber/internet/StartTask.do?taskInfoOID=cyberIBAN&token=%s' % self.page.build_token(self.token), base=True)
        self.location(url)
        # Sometimes we can't choose an account
        if account.type in [Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET] or (self.page.need_to_go() and not self.page.go_iban(account)):
            return NotAvailable
        return self.page.get_iban(account.id)

    @retry(LoggedOut)
    @need_login
    def get_account(self, id):
        return find_object(self.get_accounts_list(False), id=id)

    def set_gocardless_transaction_details(self, transaction):
        # Setting references for a GoCardless transaction
        data = self.page.get_params()
        data['validationStrategy'] = self.page.get_gocardless_strategy_param(transaction)
        data['dialogActionPerformed'] = 'DETAIL_ECRITURE'
        attribute_key, attribute_value = self.page.get_transaction_table_id(transaction._ref)
        data[attribute_key] = attribute_value
        data['token'] = self.page.build_token(data['token'])

        self.location(self.absurl('/cyber/internet/ContinueTask.do', base=True), data=data)
        ref = self.page.get_reference()
        transaction.raw = '%s %s' % (transaction.raw, ref)

        # Needed to preserve navigation.
        btn = self.page.doc.xpath('.//button[span[text()="Retour"]]')
        if len(btn):
            _data = self.page.get_params()
            actions = self.page.get_button_actions()
            _data.update(actions[btn[0].attrib['id']])
            _data['token'] = self.page.build_token(_data['token'])
            self.location('/cyber/internet/ContinueTask.do', data=_data)

    @retry(LoggedOut)
    @need_login
    def get_history(self, account, coming=False):
        account = self.get_account(account.id)

        if account is None:
            raise BrowserUnavailable()

        if account._invest_params or (account.id.startswith('TIT') and account._params):
            if not coming:
                for tr in self.get_invest_history(account):
                    yield tr
            return

        if coming:
            params = account._coming_params
        else:
            params = account._params

        if params is None:
            return

        params['token'] = self.page.build_token(params['token'])

        self.location(self.absurl('/cyber/internet/ContinueTask.do', base=True), data=params)

        if not self.page or self.error_page.is_here() or self.page.no_operations():
            return

        # Sort by values dates (see comment in TransactionsPage.get_history)
        if len(self.page.doc.xpath('//a[@id="tcl4_srt"]')) > 0:
            form = self.page.get_form(id='myForm')
            form.url = self.absurl('/cyber/internet/Sort.do?property=tbl1&sortBlocId=blc2&columnName=dateValeur')
            params['token'] = self.page.build_token(params['token'])
            form.submit()

        transactions_next_page = True

        while transactions_next_page:
            assert self.transactions_page.is_here()

            transaction_list = self.page.get_history(account, coming)
            for tr in transaction_list:
                # Add information about GoCardless
                if 'GoCardless' in tr.label and tr._has_link:
                    self.set_gocardless_transaction_details(tr)
                yield tr

            next_params = self.page.get_next_params()
            # Go to the next transaction page only if it exists:
            if next_params is None:
                transactions_next_page = False
            else:
                self.location('/cyber/internet/Page.do', params=next_params)

    @need_login
    def go_investments(self, account, get_account=False):

        if not account._invest_params and not (account.id.startswith('TIT') or account.id.startswith('PRV')):
            raise NotImplementedError()

        if get_account:
            account = self.get_account(account.id)

        if account._params:
            params = {'taskInfoOID':            "ordreBourseCTJ",
                      'controlPanelTaskAction': "true",
                      'token':                  self.page.build_token(account._params['token'])
                     }
            self.location(self.absurl('/cyber/internet/StartTask.do', base=True), params=params)
        else:
            params = account._invest_params
            params['token'] = self.page.build_token(params['token'])
            try:
                self.location(self.absurl('/cyber/internet/ContinueTask.do', base=True), data=params)
            except BrowserUnavailable:
                return False

        if self.error_page.is_here():
            raise NotImplementedError()

        url, params = self.page.get_investment_page_params()
        if params:
            try:
                self.location(url, data=params)
            except BrowserUnavailable:
                return False

            if "linebourse" in self.url:
                self.linebourse.session.cookies.update(self.session.cookies)
                self.linebourse.invest.go()

            if self.natixis_error_page.is_here():
                self.logger.warning("natixis site doesn't work")
                return False

            if self.natixis_redirect.is_here():
                url = self.page.get_redirect()
                if re.match(r'https://www.assurances.natixis.fr/etna-ihs-bp/#/equipement;codeEtab=\d+\?windowId=[a-f0-9]+$', url):
                    self.logger.warning('there may be no contract associated with %s, skipping', url)
                    return False
        return True

    @need_login
    def get_investment(self, account):
        if account.type in (Account.TYPE_LOAN,):
            self.investments[account.id] = []
            return []

        # Add "Liquidities" investment if the account is a "Compte titres PEA":
        if account.type == Account.TYPE_PEA and account.id.startswith('CPT'):
            self.investments[account.id] = [create_french_liquidity(account.balance)]
            return self.investments[account.id]

        if account.id in self.investments.keys() and self.investments[account.id] is False:
            raise NotImplementedError()

        if account.id not in self.investments.keys():
            self.investments[account.id] = []
            try:
                if self.go_investments(account, get_account=True):
                    # Redirection URL is https://www.linebourse.fr/ReroutageSJR
                    if "linebourse" in self.url:
                        # Eliminating the 3 letters prefix to match IDs on Linebourse:
                        linebourse_id = account.id[3:]
                        for inv in self.linebourse.iter_investment(linebourse_id):
                            self.investments[account.id].append(inv)

                    if self.etna.is_here():
                        params = self.page.params
                    elif self.natixis_redirect.is_here():
                        # the url may contain a "#", so we cannot make a request to it, the params after "#" would be dropped
                        url = self.page.get_redirect()
                        self.logger.debug('using redirect url %s', url)
                        m = self.etna.match(url)
                        if not m:
                            # url can be contratPrev which is not investments
                            self.logger.debug('Unable to handle this kind of contract')
                            raise NotImplementedError()

                        params = m.groupdict()

                    if self.natixis_redirect.is_here() or self.etna.is_here():
                        try:
                            self.natixis_invest.go(**params)
                        except ServerError:
                            # Broken website .. nothing to do.
                            self.investments[account.id] = iter([])
                            return self.investments[account.id]
                        self.investments[account.id] = list(self.page.get_investments())
            except NotImplementedError:
                self.investments[account.id] = []
        return self.investments[account.id]

    @need_login
    def get_invest_history(self, account):
        if not self.go_investments(account):
            return
        if "linebourse" in self.url:
            for tr in self.linebourse.iter_history(re.sub('[^0-9]', '', account.id)):
                yield tr
            return

        if self.etna.is_here():
            params = self.page.params
        elif self.natixis_redirect.is_here():
            url = self.page.get_redirect()
            self.logger.debug('using redirect url %s', url)
            m = self.etna.match(url)
            if not m:
                # url can be contratPrev which is not investments
                self.logger.debug('Unable to handle this kind of contract')
                return

            params = m.groupdict()
        else:
            return

        self.natixis_history.go(**params)
        items_from_json = list(self.page.get_history())
        items_from_json.sort(reverse=True, key=lambda item: item.date)

        years = list(set(item.date.year for item in items_from_json))
        years.sort(reverse=True)

        for year in years:
            try:
                self.natixis_pdf.go(year=year, **params)
            except HTTPNotFound:
                self.logger.debug('no pdf for year %s, fallback on json transactions', year)
                for tr in items_from_json:
                    if tr.date.year == year:
                        yield tr
            except ServerError:
                return
            else:
                history = list(self.page.get_history())
                history.sort(reverse=True, key=lambda item: item.date)
                for tr in history:
                    yield tr

    @need_login
    def get_profile(self):
        self.location('/cyber/internet/StartTask.do?taskInfoOID=accueil&token=%s' % self.token)
        return self.page.get_profile()

    @retry(LoggedOut)
    @need_login
    def get_advisor(self):
        for taskInfoOID in ['accueil', 'contacter']:
            data = OrderedDict([('taskInfoOID', taskInfoOID), ('token', self.token)])
            self.location(self.absurl('/cyber/internet/StartTask.do', base=True), params=data)
            if taskInfoOID == "accueil":
                advisor = self.page.get_advisor()
                if not advisor:
                    break
            else:
                self.page.update_agency(advisor)
        return iter([advisor])


class iter_retry(object):
    # when the callback is retried, it will create a new iterator, but we may already yielded
    # some values, so we need to keep track of them and seek in the middle of the iterator

    def __init__(self, cb, remaining=4, value=None, exc_check=Exception, logger=None):
        self.cb = cb
        self.it = value
        self.items = []
        self.remaining = remaining
        self.exc_check = exc_check
        self.logger = logger

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining <= 0:
            raise BrowserUnavailable('Site did not reply successfully after multiple tries')

        if self.it is None:
            self.it = self.cb()

            # recreated iterator, consume previous items
            try:
                nb = -1
                for nb, sent in enumerate(self.items):
                    new = next(self.it)
                    if hasattr(new, 'to_dict'):
                        equal = sent.to_dict() == new.to_dict()
                    else:
                        equal = sent == new
                    if not equal:
                        # safety is not guaranteed
                        raise BrowserUnavailable('Site replied inconsistently between retries, %r vs %r', sent, new)
            except StopIteration:
                raise BrowserUnavailable('Site replied fewer elements (%d) than last iteration (%d)', nb + 1, len(self.items))
            except self.exc_check as exc:
                if self.logger:
                    self.logger.info('%s raised, retrying', exc)
                self.it = None
                self.remaining -= 1
                return next(self)

        # return one item
        try:
            obj = next(self.it)
        except self.exc_check as exc:
            if self.logger:
                self.logger.info('%s raised, retrying', exc)
            self.it = None
            self.remaining -= 1
            return next(self)
        else:
            self.items.append(obj)
            return obj

    next = __next__

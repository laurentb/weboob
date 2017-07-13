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


import re
import json

from functools import wraps

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ClientError, ServerError
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.capabilities.bank import Account, Transaction, AccountNotFound
from weboob.capabilities.base import find_object

from .pages import LogoutPage, InfosPage, AccountsPage, HistoryPage, LifeinsurancePage, MarketPage, AdvisorPage, \
    LoginPage


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

            for i in xrange(tries, 0, -1):
                try:
                    ret = cb()
                except exc_check as exc:
                    browser.do_login()
                    browser.logger.info('%s raised, retrying', exc)
                    continue

                if not hasattr(ret, 'next'):
                    return ret  # simple value, no need to retry on items
                return iter_retry(cb, browser, value=ret, remaining=i, exc_check=exc_check, logger=browser.logger)

            raise BrowserUnavailable('Site did not reply successfully after multiple tries')

        return wrapper
    return decorator


class CmsoParBrowser(LoginBrowser):
    login = URL('/securityapi/tokens',
                '/auth/checkuser', LoginPage)
    logout = URL('/securityapi/revoke',
                 '/auth/errorauthn', LogoutPage)
    infos = URL('/comptes/', InfosPage)
    accounts = URL('/domiapi/oauth/json/accounts/synthese(?P<type>.*)', AccountsPage)
    history = URL('/domiapi/oauth/json/accounts/(?P<page>.*)', HistoryPage)
    loans = URL('/creditapi/rest/oauth/v1/synthese', AccountsPage)
    lifeinsurance = URL('/assuranceapi/v1/oauth/sso/suravenir/DETAIL_ASSURANCE_VIE/(?P<accid>.*)',
                        'https://domiweb.suravenir.fr/', LifeinsurancePage)
    market = URL('/domiapi/oauth/json/ssoDomifronttitre',
                 'https://www.(?P<website>.*)/domifronttitre/front/sso/domiweb/01/(?P<action>.*)Portefeuille\?csrf=',
                 'https://www.*/domiweb/prive/particulier', MarketPage)
    advisor = URL('/edrapi/v(?P<version>\w+)/oauth/(?P<page>\w+)', AdvisorPage)

    def __init__(self, website, *args, **kwargs):
        super(CmsoParBrowser, self).__init__(*args, **kwargs)

        self.BASEURL = "https://mon.%s" % website
        self.name = website.split('.')[0]
        self.website = website
        arkea = {'cmso.com': "03", 'cmb.fr': "01", 'cmmc.fr': '02'}
        self.arkea = arkea[website]
        self.accounts_list = []
        self.logged = False

    def deinit(self):
        if self.page and self.page.logged:
            try:
                self.logout.go(method='DELETE')
            except ClientError:
                pass

        super(CmsoParBrowser, self).deinit()

    def do_login(self):
        self.session.headers = {}
        self.session.cookies.clear()
        self.accounts_list = []

        data = {
            'accessCode': self.username,
            'password': self.password,
            'clientId': 'com.arkea.%s.siteaccessible' % self.name,
            'redirectUri': '%s/auth/checkuser' % self.BASEURL,
            'errorUri': '%s/auth/errorauthn' % self.BASEURL
        }

        self.location('/securityapi/tokens', data=data)

        if self.logout.is_here():
            raise BrowserIncorrectPassword

        m = re.search('access_token=([^&]+).*id_token=(.*)', self.url)

        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authentication': "Bearer %s" % m.group(2),
            'Authorization': "Bearer %s" % m.group(1),
            'X-ARKEA-EFS': self.arkea,
            'X-Csrf-Token': m.group(1)
        })

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    @retry((ClientError, ServerError))
    @need_login
    def iter_accounts(self):
        if self.accounts_list:
            return self.accounts_list

        seen = {}

        # First get all checking accounts...
        data = dict(self.infos.stay_or_go().get_typelist())
        self.accounts.go(data=json.dumps(data), type='comptes').check_response()
        for key in self.page.get_keys():
            for a in self.page.iter_accounts(key=key):
                self.accounts_list.append(a)
                seen[a._index] = a

        # Next, get saving accounts
        numbers = self.page.get_numbers()
        for key in self.accounts.go(data=json.dumps({}), type='epargne').get_keys():
            for a in self.page.iter_products(key=key, numbers=numbers):
                if a._index in seen:
                    self.logger.warning('skipping %s because it seems to be a duplicate of %s', a, seen[a._index])
                    continue
                self.accounts_list.append(a)

        # Then, get loans
        for key in self.loans.go().get_keys():
            for a in self.page.iter_loans(key=key):
                self.accounts_list.append(a)
        return self.accounts_list


    @retry((ClientError, ServerError))
    @need_login
    def iter_history(self, account):
        account = self.get_account(account.id)

        if account.type is Account.TYPE_LOAN:
            return iter([])

        if account.type == Account.TYPE_LIFE_INSURANCE:
            url = json.loads(self.lifeinsurance.go(accid=account._index).content)['url']
            url = self.location(url).page.get_link(u"opérations")

            return self.location(url).page.iter_history()
        elif account.type == Account.TYPE_MARKET:

            self.location(json.loads(self.market.go(data=json.dumps({'place': 'SITUATION_PORTEFEUILLE'})).content)['urlSSO'])
            self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded'

            if not self.market.go(website=self.website, action='historique').get_list(account.label):
                return iter([])

            if not self.page.get_full_list():
                return iter([])

            # Display code ISIN
            del self.session.headers['Content-Type']
            history = self.location(self.url, params={'reload': 'oui', 'convertirCode': 'oui'}).page.iter_history()
            self.session.headers['Content-Type'] = 'application/json'

            return history

        # Getting a year of history
        nbs = ["UN", "DEUX", "TROIS", "QUATRE", "CINQ", "SIX", "SEPT", "HUIT", "NEUF", "DIX", "ONZE", "DOUZE"]
        trs = []

        self.history.go(data=json.dumps({"index": account._index}), page="pendingListOperations")

        has_deferred_cards = self.page.has_deferred_cards()

        self.history.go(data=json.dumps({'index': account._index}), page="detailcompte")

        self.trs = {'lastdate': None, 'list': []}

        for tr in self.page.iter_history(index=account._index, nbs=nbs):
            if has_deferred_cards and tr.type == Transaction.TYPE_CARD:
                tr.type = Transaction.TYPE_DEFERRED_CARD

            trs.append(tr)

        return trs

    @retry((ClientError, ServerError))
    @need_login
    def iter_coming(self, account):
        account = self.get_account(account.id)

        if account.type is Account.TYPE_LOAN:
            return iter([])

        comings = []

        self.history.go(data=json.dumps({"index": account._index}), page="pendingListOperations")

        for key in self.page.get_keys():
            self.trs = {'lastdate': None, 'list': []}
            for c in self.page.iter_history(key=key):
                if hasattr(c, '_deferred_date'):
                    c.date = c._deferred_date
                    c.type = Transaction.TYPE_DEFERRED_CARD # force deferred card type for comings inside cards

                c.vdate = None # vdate don't work for comings

                comings.append(c)
        return iter(comings)

    @retry((ClientError, ServerError))
    @need_login
    def iter_investment(self, account):
        account = self.get_account(account.id)

        if account.type == Account.TYPE_LIFE_INSURANCE:
            url = json.loads(self.lifeinsurance.go(accid=account._index).content)['url']
            url = self.location(url).page.get_link("supports")
            if not url:
                return iter([])
            return self.location(url).page.iter_investment()
        elif account.type == Account.TYPE_MARKET:
            self.location(json.loads(self.market.go(data=json.dumps({"place": \
                          "SITUATION_PORTEFEUILLE"})).content)['urlSSO'])

            return self.page.iter_investment() if self.market.go(website=self.website, \
                        action="situation").get_list(account.label) else iter([])
        raise NotImplementedError()

    @retry((ClientError, ServerError))
    @need_login
    def get_advisor(self):
        advisor = self.advisor.go(version="2", page="conseiller").get_advisor()
        return iter([self.advisor.go(version="1", page="agence").update_agency(advisor)])


class iter_retry(object):
    # when the callback is retried, it will create a new iterator, but we may already yielded
    # some values, so we need to keep track of them and seek in the middle of the iterator

    def __init__(self, cb, browser, remaining=4, value=None, exc_check=Exception, logger=None):
        self.cb = cb
        self.it = value
        self.items = []
        self.remaining = remaining
        self.exc_check = exc_check
        self.logger = logger
        self.browser = browser
        self.delogged = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining <= 0:
            raise BrowserUnavailable('Site did not reply successfully after multiple tries')
        if self.delogged:
            self.browser.do_login()

        self.delogged = False

        if self.it is None:
            self.it = self.cb()

            # recreated iterator, consume previous items
            try:
                nb = -1
                for nb, sent in enumerate(self.items):
                    new = next(self.it)
                    if hasattr(new, 'iter_fields'):
                        equal = dict(sent.iter_fields()) == dict(new.iter_fields())
                    else:
                        equal = sent == new
                    if not equal:
                        # safety is not guaranteed
                        raise BrowserUnavailable('Site replied inconsistently between retries, %r vs %r', sent, new)
            except StopIteration:
                raise BrowserUnavailable('Site replied fewer elements (%d) than last iteration (%d)', nb + 1, len(self.items))
            except self.exc_check as exc:
                self.delogged = True
                if self.logger:
                    self.logger.info('%s raised, retrying', exc)
                self.it = None
                self.remaining -= 1
                return next(self)

        # return one item
        try:
            obj = next(self.it)
        except self.exc_check as exc:
            self.delogged = True
            if self.logger:
                self.logger.info('%s raised, retrying', exc)
            self.it = None
            self.remaining -= 1
            return next(self)
        else:
            self.items.append(obj)
            return obj

    next = __next__

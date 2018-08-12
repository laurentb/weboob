# -*- coding: utf-8 -*-

# Copyright(C) 2015      Oleg Plakhotniuk
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

from requests.exceptions import ConnectionError, Timeout

from weboob.browser import URL, LoginBrowser, need_login
from weboob.browser.exceptions import ServerError
from weboob.browser.pages import HTMLPage
from weboob.capabilities.bank import Account, AccountNotFound, Transaction
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import AmericanTransaction as AmTr
from weboob.tools.compat import unicode

__all__ = ['VicSecCard']


class SomePage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath(u'//span[text()="Sign Out"]'))


class LoginPage(SomePage):
    def login(self, username, password):
        form = self.get_form(name='frmLogin')
        form['username_input'] = username
        form['userName'] = username
        form['password_input'] = password
        form['hiddenPassword'] = password
        form['btnLogin'] = 'btnLogin'
        form.submit()


class HomePage(SomePage):
    def account(self):
        id_ = self.doc.xpath(u'//strong[contains(text(),'
                             u'"Credit Card account ending in")]/text()')[0].strip()[-4:]
        balance = self.doc.xpath(
            u'//span[@class="description" and text()="Current Balance"]/../span[@class="total"]/text()')[0].strip()
        cardlimit = self.doc.xpath(u'//span[contains(text(),"Credit limit")]'
                                   u'/text()')[0].split()[-1]
        paymin = self.doc.xpath(u'//section[@id=" account_summary"]'
                                u'//strong[text()="Minimum Payment Due"]/../../span[2]/text()'
                                )[0].strip()
        a = Account()
        a.id = id_
        a.label = u'ACCOUNT ENDING IN %s' % id_
        a.currency = Account.get_currency(balance)
        a.balance = -AmTr.decimal_amount(balance)
        a.type = Account.TYPE_CARD
        a.cardlimit = AmTr.decimal_amount(cardlimit)
        a.paymin = AmTr.decimal_amount(paymin)
        # TODO: Add paydate.
        # Oleg: I don't have an account with scheduled payment.
        #       Need to wait for a while...
        return a


class RecentPage(SomePage):
    def iter_transactions(self):
        for li in self.doc.xpath('//section[@class="transactions"]//div/li'):
            date = li.xpath('p[@data-type="date"]//text()')[0].strip()
            label = li.xpath('p[@data-type="description"]//text()')[0].strip()
            amount = li.xpath('p[@data-type="amount"]//text()')[0].strip()
            t = Transaction()
            t.date = datetime.strptime(date, '%m/%d/%Y')
            t.rdate = datetime.strptime(date, '%m/%d/%Y')
            t.type = Transaction.TYPE_UNKNOWN
            t.raw = unicode(label)
            t.label = unicode(label)
            t.amount = -AmTr.decimal_amount(amount)
            yield t


class VicSecCard(LoginBrowser):
    BASEURL = 'https://c.comenity.net'
    MAX_RETRIES = 10
    TIMEOUT = 30.0
    login = URL(r'/victoriassecret/$', LoginPage)
    home = URL(r'/victoriassecret/secure/SecureHome.xhtml', HomePage)
    recent = URL(r'/victoriassecret/secure/accountactivity/Transactions.xhtml',
                 RecentPage)
    unknown = URL('.*', SomePage)

    def get_account(self, id_):
        a = next(self.iter_accounts())
        if (a.id != id_):
            raise AccountNotFound()
        return a

    @need_login
    def iter_accounts(self):
        yield self.home.stay_or_go().account()

    @need_login
    def iter_history(self, account):
        for trans in self.recent.stay_or_go().iter_transactions():
            yield trans

    def do_login(self):
        self.session.cookies.clear()
        self.login.go().login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    def location(self, *args, **kwargs):
        for i in range(self.MAX_RETRIES):
            try:
                return super(VicSecCard, self).location(*args, **kwargs)
            except (ServerError, Timeout, ConnectionError) as e:
                last_error = e
        raise last_error

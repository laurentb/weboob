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

from weboob.capabilities.bank import AccountNotFound, Account, Transaction
from weboob.tools.capabilities.bank.transactions import \
    AmericanTransaction as AmTr
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.pages import HTMLPage
from weboob.exceptions import BrowserIncorrectPassword
from datetime import datetime


__all__ = ['VicSecCard']


class SomePage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath(u'//a[text()="Sign out"]'))


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
        id_ = self.doc.xpath(u'//h1[contains(text(),'
            '"Information for account ending in")]/text()')[0].strip()[-4:]
        balance = self.amount(u'Current balance')
        cardlimit = self.amount(u'Credit limit')
        paymin = self.amount(u'Minimum payment')
        a = Account()
        a.id = id_
        a.label = u'ACCOUNT ENDING IN %s' % id_
        a.currency = Account.get_currency(balance)
        a.balance = -AmTr.decimal_amount(balance)
        a.type = Account.TYPE_CARD
        a.cardlimit = AmTr.decimal_amount(cardlimit)
        a.paymin = AmTr.decimal_amount(paymin)
        #TODO: Add paydate.
        #Oleg: I don't have an account with scheduled payment.
        #      Need to wait for a while...
        return a

    def amount(self, name):
        return self.doc.xpath(
            u'//td[contains(text(),"%s")]/../td[2]/text()' % name)[0].strip()


class RecentPage(SomePage):
    def iter_transactions(self):
        for tr in self.doc.xpath('//table[@id="allTransactionList_table1"]'
                                 '/tbody/tr'):
            date = tr.xpath('td[1]/text()')[0]
            label = u''.join(x.strip() for x in tr.xpath('td[2]/a/text()') +
                                                tr.xpath('td[2]/text()'))
            amount = tr.xpath('td[4]/text()')[0]
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

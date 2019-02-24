# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import Cookie
import datetime
import itertools
import json
import os
import re
from decimal import Decimal
from time import sleep

from requests.cookies import morsel_to_cookie

from weboob.browser.pages import HTMLPage, LoggedPage, RawPage
from weboob.capabilities.bank import Account, Transaction
from weboob.tools.capabilities.bank.transactions import AmericanTransaction as AmTr

from .parsers import StatementParser, clean_label


try:
    cmp = cmp
except NameError:
    def cmp(x, y):
        return (x > y) - (x < y)


class LoginProceedPage(LoggedPage, HTMLPage):
    is_here = '//script[contains(text(),"setAndCheckCookie")]'

    def proceed(self):
        script = self.doc.xpath('//script/text()')[0]
        cookieStr = re.match('.*document\.cookie = "([^"]+)".*',
                             script, re.DOTALL).group(1)
        morsel = Cookie.Cookie(cookieStr).values()[0]
        self.browser.session.cookies.set_cookie(morsel_to_cookie(morsel))
        form = self.get_form()
        return form.submit()


class LoginRedirectPage(LoggedPage, HTMLPage):
    is_here = 'contains(//meta[@http-equiv="Refresh"]/@content,' \
                       '"SIGNON_PORTAL_PAUSE")'

    def redirect(self):
        refresh = self.doc.xpath(
            '//meta[@http-equiv="Refresh"]/@content')[0]
        url = re.match(r'^.*URL=(.*)$', refresh).group(1)
        return self.browser.location(url)


class LoggedInPage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath(u'//a[text()="Sign Off"]')) \
            or bool(self.doc.xpath(u'//title[text()="Splash Page"]')) \
            or bool(self.doc.xpath(u'//title[contains(text(),'
                                   u'"Advanced Access Required")]'))


class CodeRequestPage(LoggedInPage):
    is_here = u'contains(//label/text(),"Send Code to")'

    def request_code(self):
        phone = self.browser.page.doc.xpath(
            '//select[@name="telephone"]/option[contains(text(),"%s")]/@value'
            % self.browser.phone_last4)[0]
        form = self.get_form(name='otp')
        form['telephone'] = [phone]
        form['deliveryMode'] = ['sms']
        form['sendcode'] = ['Request Code']
        del form['cancelBtn']
        del form['sendcode2']
        return form.submit()


class CodeSubmitPage(LoggedInPage):
    is_here = u'contains(//title/text(),"Enter and Submit Advanced Access Code")'

    def submit_code(self):
        self.browser.logger.warning(
            'The code has been sent to the phone number ending with %s. '
            'Please write this code into the file %s'
            % (self.browser.phone_last4, self.browser.code_file))
        while True:
            try:
                with open(self.browser.code_file) as f:
                    code = f.read().strip()
                break
            except IOError:
                sleep(1)
        os.remove(self.browser.code_file)
        self.browser.logger.info('The code %s has been successfully read' % code)
        form = self.get_form(name='otp')
        form['passcode'] = [code]
        del form['cancelBtn']
        del form['btnSubmit']
        return form.submit()


class SummaryPage(LoggedInPage):
    is_here = u'//title[contains(text(),"Account Summary")]'

    def to_activity(self):
        href = self.doc.xpath(u'//a[text()="Account Activity"]/@href')[0]
        self.browser.location(href)

    def to_documents(self):
        href = self.doc.xpath('//a[text()="Statements & Documents"]'
                              '/@href')[0]
        self.browser.location(href)


class AccountPage(object):
    def account_id(self, name=None):
        if name:
            return name[-4:]  # Last 4 digits of "BLAH XXXXXXX1234"
        else:
            return self.account_id(self.account_name())


class ActivityPage(AccountPage, LoggedInPage):
    def is_here(self):
        return bool(self.doc.xpath(
            u'contains(//title/text(),"Account Activity")'))

    def accounts_names(self):
        return self.doc.xpath(
            u'//select[@name="selectedAccountUID"]/option/text()')

    def accounts_ids(self):
        return [self.account_id(name) for name in self.accounts_names()]

    def account_uid(self, id_=None):
        if id_:
            return self.doc.xpath(
                u'//select[@name="selectedAccountUID"]'
                u'/option[contains(text(),"%s")]/@value' % id_)[0]
        else:
            return self.doc.xpath(
                u'//select[@name="selectedAccountUID"]'
                u'/option[@selected="selected"]/@value')[0]

    def account_name(self):
        for name in self.doc.xpath(u'//select[@name="selectedAccountUID"]'
                                   u'/option[@selected="selected"]/text()'):
            return name
        return u''

    def account_type(self, name=None):
        raise NotImplementedError()

    def account_balance(self):
        raise NotImplementedError()

    def account_paydatemin(self):
        return None, None

    def account_cardlimit(self):
        return None

    def to_account(self, id_):
        form = self.get_form(xpath='//form[@name="AccountActivityForm"]')
        form['selectedAccountUID'] = [self.account_uid(id_)]
        form.submit()

    def get_account(self):
        name = self.account_name()
        balance = self.account_balance()
        currency = Account.get_currency(balance)
        id_ = self.account_id()
        type_ = self.account_type()
        paydate, paymin = self.account_paydatemin()
        cardlimit = self.account_cardlimit()

        account = Account()
        account.id = id_
        account.label = name
        account.currency = currency
        account.balance = AmTr.decimal_amount(balance)
        account.type = type_
        if paydate is not None:
            account.paydate = paydate
        if paymin is not None:
            account.paymin = paymin
        if cardlimit is not None:
            account.cardlimit = AmTr.decimal_amount(cardlimit)

        return account

    def since_last_statement(self):
        raise NotImplementedError()

    def iter_transactions(self):
        raise NotImplementedError()

    def next_(self):
        raise NotImplementedError()


class ActivityCashPage(ActivityPage):
    def is_here(self):
        return super(ActivityCashPage, self).is_here() and \
            (u'CHECKING' in self.account_name() or
             u'SAVINGS' in self.account_name())

    def account_type(self, name=None):
        name = name or self.account_name()
        if u'CHECKING' in name:
            return Account.TYPE_CHECKING
        elif u'SAVINGS' in name:
            return Account.TYPE_SAVINGS
        else:
            return Account.TYPE_UNKNOWN

    def account_balance(self):
        return self.doc.xpath(
            u'//td[@headers="currentPostedBalance"]/span/text()')[0]

    def since_last_statement(self):
        if not self.doc.xpath(u'//p[@id="noactivitymessage"]'):
            form = self.get_form(xpath='//form[@id="ddaShowForm"]')
            form['showTabDDACommand.transactionTypeFilterValue'] = [
                u'All Transactions']
            form['showTabDDACommand.timeFilterValue'] = ['8']
            form.submit()
            return True

    def iter_transactions(self):
        for row in self.doc.xpath('//tr/th[@headers='
                                  '"postedHeader dateHeader"]/..'):
            date = row.xpath('th[@headers="postedHeader '
                             'dateHeader"]/text()')[0]
            desc = row.xpath('td[@headers="postedHeader descriptionHeader"]'
                             '//span[@class="OneLinkNoTx"]/text()')[0]
            deposit = row.xpath('td[@headers="postedHeader '
                                'depositsConsumerHeader"]/span/text()')[0]
            withdraw = row.xpath('td[@headers="postedHeader '
                                 'withdrawalsConsumerHeader"]/span/text()')[0]

            date = datetime.datetime.strptime(date, '%m/%d/%y')

            desc = clean_label(desc)

            deposit = deposit.strip()
            deposit = AmTr.decimal_amount(deposit or '0')
            withdraw = withdraw.strip()
            withdraw = AmTr.decimal_amount(withdraw or '0')

            amount = deposit - withdraw

            trans = Transaction(u'')
            trans.date = date
            trans.rdate = date
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = amount
            yield trans

    def next_(self):
        links = self.doc.xpath('//a[@title="Go To Next Page"]/@href')
        if links:
            self.browser.location(links[0])
            return True
        else:
            return False


class ActivityCardPage(ActivityPage):
    def is_here(self):
        return super(ActivityCardPage, self).is_here() and \
            u'CARD' in self.account_name()

    def account_type(self, name=None):
        return Account.TYPE_CARD

    def account_balance(self):
        return self.doc.xpath(
            u'//td[@headers="outstandingBalance"]/text()')[0]

    def account_cardlimit(self):
        return self.doc.xpath(
            u'//td[@headers="totalCreditLimit"]/text()')[0]

    def account_paydatemin(self):
        if self.doc.xpath(u'//p[contains(text(),'
                          '"payment due date is not yet scheduled")]'):
            # If payment date is not scheduled yet, set it somewhere in a
            # distant future, so that we always have a valid date.
            return datetime.datetime.now() + datetime.timedelta(days=999), \
                   Decimal(0)
        else:
            date = self.doc.xpath(u'//span[contains(text(),"Minimum Payment")]'
                                   '/span/text()')[0]
            date = re.match(u'.*(../../..).*', date).group(1)
            date = datetime.datetime.strptime(date, '%m/%d/%y')
            amount = self.doc.xpath(u'//td[@headers="minimumPaymentDue"]'
                                     '//text()')[0].strip()
            return date, AmTr.decimal_amount(amount)

    def get_account(self):
        account = ActivityPage.get_account(self)

        # Credit card is essentially a liability.
        # Negative amount means there's a payment due.
        account.balance = -account.balance

        return account

    def since_last_statement(self):
        if self.doc.xpath('//select[@name="showTabCommand.'
                                          'transactionTypeFilterValue"]'
                          '/option[@value="sincelastStmt"]'):
            form = self.get_form(xpath='//form[@id="creditCardShowForm"]')
            form['showTabCommand.transactionTypeFilterValue'] = [
                'sincelastStmt']
            form.submit()
            return True

    def iter_transactions(self):
        for row in self.doc.xpath('//tr/th[@headers='
                                  '"postedHeader transactionDateHeader"]/..'):
            tdate = row.xpath('th[@headers="postedHeader '
                              'transactionDateHeader"]/text()')[0]
            pdate = row.xpath('td[@headers="postedHeader '
                              'postingDateHeader"]/text()')[0]
            desc = row.xpath('td[@headers="postedHeader '
                              'descriptionHeader"]/span/text()')[0]
            ref = row.xpath('td[@headers="postedHeader '
                             'descriptionHeader"]/text()')[0]
            amount = row.xpath('td[@headers="postedHeader '
                               'amountHeader"]/text()')[0]

            tdate = datetime.datetime.strptime(tdate, '%m/%d/%y')
            pdate = datetime.datetime.strptime(pdate, '%m/%d/%y')

            desc = clean_label(desc)

            ref = re.match('.*<REFERENCE ([^>]+)>.*', ref).group(1)

            if amount.startswith('+'):
                amount = AmTr.decimal_amount(amount[1:])
            else:
                amount = -AmTr.decimal_amount(amount)

            trans = Transaction(ref)
            trans.date = tdate
            trans.rdate = pdate
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = amount
            yield trans

    def next_(self):
        # As of 2014-07-05, there's only one page for cards history.
        return False


class DocumentsPage(LoggedInPage):
    HEADER_XPATH = u'//h1[contains(text(),"Statements and Documents")]'
    LINK_XPATH = u'//a[@data-async-load-template="stmtdisc.html"]' \
                 u'/@data-async-load-url'

    def is_here(self):
        return self.doc.xpath(self.HEADER_XPATH) \
           and self.doc.xpath(self.LINK_XPATH)

    def to_statements(self):
        url = self.doc.xpath(self.LINK_XPATH)[0]
        self.browser.location(url)


class StatementsEmbeddedPage(LoggedInPage):
    HEADER_XPATH = u'//h1[contains(text(),"Statements and Documents")]'
    SCRIPT_XPATH = '//script[contains(text(),"stmtdisc.html")]/text()'

    def is_here(self):
        return self.doc.xpath(self.HEADER_XPATH) \
           and self.doc.xpath(self.SCRIPT_XPATH)

    def get_embedded_data(self):
        scr = self.doc.xpath(self.SCRIPT_XPATH)[0]
        data = json.loads('\n'.join(scr.split('\n')[2:-2]).replace(
            "'appendTo'", '"appendTo"'))
        return json.loads(data['data'])

    def parser(self):
        return StatementsPageParser(self.get_embedded_data(), self.browser)


class WfJsonPage(LoggedPage, RawPage):
    def __init__(self, *args, **kwArgs):
        RawPage.__init__(self, *args, **kwArgs)
        clean = self.doc.replace('"/*WellFargoProprietary%', '') \
            .replace('%WellFargoProprietary*/"', '').decode('string_escape')
        self.doc = json.loads(clean)


class StatementsPage(WfJsonPage):
    def parser(self):
        return StatementsPageParser(self.doc, self.browser)


class StatementsPageParser(AccountPage):
    def __init__(self, doc, browser):
        self.doc = doc
        self.browser = browser

    def account_name(self):
        for account in self.accounts():
            if account['selected']:
                return account['accountDisplayName']

    def to_account(self, id_):
        for account in self.accounts():
            if account['accountDisplayName'].endswith(id_):
                self.browser.location(account['url'])

    def year(self):
        for period in self.periods():
            if period['selected']:
                try:
                    return int(period['timePeriod'])
                except ValueError:
                    pass

    def years(self):
        for period in self.periods():
            try:
                yield int(period['timePeriod'])
            except ValueError:
                pass

    def to_year(self, year):
        for period in self.periods():
            if period['timePeriod'] == str(year):
                self.browser.location(period['url'])

    def statements(self):
        stmts = self.doc['statementsDisclosuresInfo'].get('statements', [])
        for stmt in stmts:
            yield stmt['url']

    def accounts(self):
        return self.doc['statementsDisclosuresInfo']['accountList']

    def periods(self):
        return self.doc['statementsDisclosuresInfo']['timePeriodList']


class StatementPage(LoggedPage, RawPage):
    def __init__(self, *args, **kwArgs):
        RawPage.__init__(self, *args, **kwArgs)
        self._parser = StatementParser(self.doc)

    def is_here(self):
        return self.doc[:4] == '%PDF'

    def iter_transactions(self):
        # Maintain a nice consistent newer-to-older order of transactions.
        return sorted(
            itertools.chain(
                self._parser.read_cash_transactions(),
                self._parser.read_card_transactions()),
            cmp=lambda t1, t2: cmp(t2.date, t1.date) or
                               cmp(t1.label, t2.label) or
                               cmp(t1.amount, t2.amount))

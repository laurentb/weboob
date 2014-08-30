# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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

from weboob.capabilities.bank import Account, Transaction
from weboob.tools.browser import BasePage
from weboob.tools.parsers import get_parser
from weboob.tools.parsers.iparser import IParser
from weboob.tools.mech import ClientForm
from urllib import unquote
from StringIO import StringIO
from .parsers import StatementParser, clean_amount, clean_label
import itertools
import re
import datetime

__all__ = ['LoginPage', 'LoggedInPage', 'SummaryPage']


def form_with_control(control_name):
    """
    Form search helper.
    Returns whether the form has a control with specified name.
    """
    def predicate(form):
        try:
            form.find_control(name=control_name)
        except ClientForm.ControlNotFoundError:
            return False
        else:
            return True
    return predicate


class LoginPage(BasePage):
    def login(self, login, password):
        self.browser.select_form(name='Signon')
        self.browser['userid'] = login.encode(self.browser.ENCODING)
        self.browser['password'] = password.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)


class LoginRedirectPage(BasePage):
    def is_logged(self):
        return True

    def redirect(self):
        refresh = self.document.xpath(
            '//meta[@http-equiv="Refresh"]/@content')[0]
        url = re.match(r'^.*URL=(.*)$', refresh).group(1)
        self.browser.location(url)


class LoggedInPage(BasePage):
    def is_logged(self):
        if type(self.document) is str:
            return True
        else:
            return bool(self.document.xpath(u'//a[text()="Sign Off"]')) \
                or bool(self.document.xpath(u'//title[text()="Splash Page"]'))


class SummaryPage(LoggedInPage):
    def to_activity(self):
        href = self.document.xpath(u'//a[text()="Account Activity"]/@href')[0]
        self.browser.location(href)

    def to_statements(self):
        href = self.document.xpath('//a[text()="Statements & Documents"]'
                                   '/@href')[0]
        self.browser.location(href)


class DynamicPage(LoggedInPage):
    """
    Most of Wells Fargo pages have the same URI pattern.
    Some of these pages are HTML, some are PDF.
    """
    def sub_page(self):
        page = None
        if type(self.document) is str:
            page = StatementSubPage
        elif u'Account Activity' in self._title():
            name = self._account_name()
            if u'CHECKING' in name or u'SAVINGS' in name:
                page = ActivityCashSubPage
            elif u'CARD' in name:
                page = ActivityCardSubPage
        elif u'Statements & Documents' in self._title():
            page = StatementsSubPage
        assert page
        return page(self)

    def _title(self):
        return self.document.xpath(u'//title/text()')[0]

    def _account_name(self):
        return self.document.xpath(
            u'//select[@name="selectedAccountUID"]'
            u'/option[@selected="selected"]/text()')[0]


class SubPage(object):
    def __init__(self, page):
        self.page = page


class AccountSubPage(SubPage):
    def account_id(self, name=None):
        if name:
            return name[-4:] # Last 4 digits of "BLAH XXXXXXX1234"
        else:
            return self.account_id(self.account_name())


class ActivitySubPage(AccountSubPage):
    def __init__(self, *args, **kwargs):
        AccountSubPage.__init__(self, *args, **kwargs)

        # As of 2014-07-03, there are few nested "optgroup" nodes on
        # the account activity pages, which is a violation of HTML
        # standard and cannot be parsed by mechanize's Browser.select_form.
        resp = self.page.browser.response()
        resp.set_data(re.sub('</?optgroup[^>]*>', '', resp.get_data()))
        self.page.browser.set_response(resp)

    def is_activity(self):
        return True

    def accounts_names(self):
        return self.page.document.xpath(
            u'//select[@name="selectedAccountUID"]/option/text()')

    def accounts_ids(self):
        return [self.account_id(name) for name in self.accounts_names()]

    def account_uid(self, id_=None):
        if id_:
            return self.page.document.xpath(
                u'//select[@name="selectedAccountUID"]'
                u'/option[contains(text(),"%s")]/@value' % id_)[0]
        else:
            return self.page.document.xpath(
                u'//select[@name="selectedAccountUID"]'
                u'/option[@selected="selected"]/@value')[0]

    def account_name(self):
        return self.page.document.xpath(
            u'//select[@name="selectedAccountUID"]'
            u'/option[@selected="selected"]/text()')[0]

    def account_type(self, name=None):
        raise NotImplementedError()

    def account_balance(self):
        raise NotImplementedError()

    def to_account(self, id_):
        self.page.browser.select_form(name='AccountActivityForm')
        self.page.browser['selectedAccountUID'] = [self.account_uid(id_)]
        self.page.browser.submit()

    def get_account(self):
        name = self.account_name()
        balance = self.account_balance()
        currency = Account.get_currency(balance)
        id_ = self.account_id()
        type_ = self.account_type()

        account = Account()
        account.id = id_
        account.label = name
        account.currency = currency
        account.balance = clean_amount(balance)
        account.type = type_
        return account

    def since_last_statement(self):
        raise NotImplementedError()

    def iter_transactions(self):
        raise NotImplementedError()

    def next_(self):
        raise NotImplementedError()


class ActivityCashSubPage(ActivitySubPage):
    def account_type(self, name=None):
        name = name or self.account_name()
        if u'CHECKING' in name:
            return Account.TYPE_CHECKING
        elif u'SAVINGS' in name:
            return Account.TYPE_SAVINGS
        else:
            return Account.TYPE_UNKNOWN

    def account_balance(self):
        return self.page.document.xpath(
            u'//td[@headers="currentPostedBalance"]/span/text()')[0]

    def since_last_statement(self):
        b = self.page.browser
        b.select_form(predicate=form_with_control(
            'showTabDDACommand.transactionTypeFilterValue'))
        b['showTabDDACommand.transactionTypeFilterValue'] = [
            u'All Transactions']
        b['showTabDDACommand.timeFilterValue'] = ['8']
        b.submit()

    def iter_transactions(self):
        for row in self.page.document.xpath('//tr/th[@headers='
                                            '"postedHeader dateHeader"]/..'):
            date = row.xpath('th[@headers="postedHeader '
                             'dateHeader"]/text()')[0]
            desc = row.xpath('td[@headers="postedHeader '
                             'descriptionHeader"]/div/text()')[0]
            deposit = row.xpath('td[@headers="postedHeader '
                                'depositsConsumerHeader"]/span/text()')[0]
            withdraw = row.xpath('td[@headers="postedHeader '
                                 'withdrawalsConsumerHeader"]/span/text()')[0]

            date = datetime.datetime.strptime(date, '%m/%d/%y')

            desc = clean_label(desc)

            deposit = deposit.strip()
            deposit = clean_amount(deposit or '0')
            withdraw = withdraw.strip()
            withdraw = clean_amount(withdraw or '0')

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
        links = self.page.document.xpath('//a[@title="Go To Next Page"]/@href')
        if links:
            self.page.browser.location(links[0])
            return True
        else:
            return False


class ActivityCardSubPage(ActivitySubPage):
    def account_type(self, name=None):
        return Account.TYPE_CARD

    def account_balance(self):
        return self.page.document.xpath(
            u'//td[@headers="outstandingBalance"]/text()')[0]

    def get_account(self):
        account = ActivitySubPage.get_account(self)

        # Credit card is essentially a liability.
        # Negative amount means there's a payment due.
        account.balance = -account.balance

        return account

    def since_last_statement(self):
        b = self.page.browser
        b.select_form(predicate=form_with_control(
            'showTabCommand.transactionTypeFilterValue'))
        b['showTabCommand.transactionTypeFilterValue'] = ['sincelastStmt']
        b.submit()

    def iter_transactions(self):
        for row in self.page.document.xpath('//tr/th[@headers='
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
                amount = clean_amount(amount[1:])
            else:
                amount = -clean_amount(amount)

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


class StatementsSubPage(AccountSubPage):
    def __init__(self, *args, **kwargs):
        AccountSubPage.__init__(self, *args, **kwargs)

        # As of 2014-07-06, there are few "<br/>" nodes on
        # the account statements pages, which is a violation of HTML
        # standard and cannot be parsed by mechanize's Browser.select_form.
        resp = self.page.browser.response()
        resp.set_data(re.sub('<br */>', '', resp.get_data()))
        self.page.browser.set_response(resp)

    def is_statements(self):
        return True

    def account_name(self):
        return self.page.document.xpath(
            u'//select[@name="selectedAccountKey"]'
            u'/option[@selected="selected"]/text()')[0]

    def account_uid(self, id_):
        return self.page.document.xpath(
            u'//select[@name="selectedAccountKey"]'
            u'/option[contains(text(),"%s")]/@value' % id_)[0]

    def to_account(self, id_):
        self.page.browser.select_form(predicate=form_with_control(
            'selectedAccountKey'))
        self.page.browser['selectedAccountKey'] = [self.account_uid(id_)]
        self.page.browser.submit()

    def year(self):
        for text in self.page.document.xpath('//h2/strong/text()'):
            try:
                return int(text)
            except ValueError:
                pass

    def years(self):
        for text in self.page.document.xpath('//h2//strong/text()'):
            try:
                yield int(text)
            except ValueError:
                pass

    def to_year(self, year):
        href = self.page.document.xpath('//h2/a/strong[text()="%s"]'
                                        '/../@href' % year)[0]
        self.page.browser.location(href)

    def statements(self):
        for outer_uri in self.page.document.xpath(
                                '//table[@id="listOfStatements"]'
                                '//a[contains(text(), "Statement")]/@href'):
            inner_uri = re.match('.*destinationClickUrl=([^&]+)&.*',
                                 outer_uri).group(1)
            yield unquote(inner_uri)


class StatementSubPage(SubPage):

    def __init__(self, *args, **kwArgs):
        SubPage.__init__(self, *args, **kwArgs)
        self._parser = StatementParser(self.page.document)

    def is_statement(self):
        return True

    def iter_transactions(self):
        # Maintain a nice consistent newer-to-older order of transactions.
        return sorted(
            itertools.chain(
                self._parser.read_cash_transactions(),
                self._parser.read_card_transactions()),
            cmp=lambda t1, t2: cmp(t2.date, t1.date) or
                               cmp(t1.label, t2.label) or
                               cmp(t1.amount, t2.amount))


class DynamicParser(IParser):
    def __init__(self):
        self._html = get_parser()()
        self._raw = get_parser('raw')()
        self._parser = None

    def parse(self, data, encoding=None):
        # Ugly hack to figure out the document type
        s = data.read()
        if s[:4] == '%PDF':
            self._parser = self._raw
        else:
            self._parser = self._html
        return self._parser.parse(StringIO(s), encoding)

    def __getattr__(self, name):
        assert self._parser
        return getattr(self._parser, name)

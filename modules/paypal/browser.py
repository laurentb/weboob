# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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


import datetime
from dateutil.relativedelta import relativedelta

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import LoginPage, AccountPage, UselessPage, HomePage, ProHistoryPage, PartHistoryPage, HistoryDetailsPage


__all__ = ['Paypal']


class Paypal(Browser):
    DOMAIN = 'www.paypal.com'
    PROTOCOL = 'https'
    CERTHASH = ['b8f6c76050ed3035aab08474b1da0ff783f20d114b1740e8db275fe433ff69af', '96753399cf183334cef00a72719ea8e13cfe68d1e953006348f41f884180de15']
    ENCODING = 'UTF-8'
    PAGES = {
        '/cgi-bin/webscr\?cmd=_login-run$':             LoginPage,
        '/cgi-bin/webscr\?cmd=_login-submit.+$':        LoginPage,  # wrong login
        '/cgi-bin/webscr\?cmd=_login-processing.+$':    UselessPage,
        '/cgi-bin/webscr\?cmd=_account.*$':             UselessPage,
        '/cgi-bin/webscr\?cmd=_login-done.+$':          UselessPage,
        '/cgi-bin/webscr\?cmd=_home&country_lang.x=true$': HomePage,
        'https://\w+.paypal.com/cgi-bin/webscr\?cmd=_history-details-from-hub&id=[A-Z0-9]+$': HistoryDetailsPage,
        'https://\w+.paypal.com/webapps/business/\?nav=0.0': HomePage,
        'https://\w+.paypal.com/webapps/business/\?country_lang.x=true': HomePage,
        'https://\w+.paypal.com/myaccount/\?nav=0.0': HomePage,
        'https://\w+.paypal.com/businessexp/money': AccountPage,
        'https://\w+.paypal.com/webapps/business/activity\?.*': ProHistoryPage,
        'https://\w+.paypal.com/myaccount/activity/.*': (PartHistoryPage, 'json'),
        'https://\w+.paypal.com/myaccount/': ProHistoryPage,
    }

    DEFAULT_TIMEOUT = 60

    BEGINNING = datetime.date(1998, 6, 1)  # The day PayPal was founded
    account_type = None

    def find_account_type(self):
        if self.is_on_page(HomePage):
            # XXX Unable to get more than 2 years of history on pro accounts.
            self.BEGINNING = datetime.date.today() - relativedelta(months=24)
            self.account_type = "pro"
            return
        self.location(self._response.info().getheader('refresh').split("bin/")[1])
        if self.is_on_page(AccountPage):
            self.location('/myaccount')
            self.account_type = "perso"
        else:
            self.location('/webapps/business/?nav=0.0')
            if self.is_on_page(HomePage):
                self.account_type = "pro"
            else:
                self.account_type = "perso"

    def home(self):
        self.location('https://' + self.DOMAIN + '/en/cgi-bin/webscr?cmd=_login-run')

    def is_logged(self):
        # TODO Does not handle disconnect mid-session
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN + '/en/cgi-bin/webscr?cmd=_login-run')

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        self.find_account_type()

    def get_accounts(self):
        if not self.is_on_page(AccountPage):
            self.location('/businessexp/money')

        return self.page.get_accounts()

    def get_account(self, _id):
        if not self.is_on_page(AccountPage):
            self.location('/businessexp/money')

        return self.page.get_account(_id)

    def get_download_history(self, account, step_min=None, step_max=None):
        if step_min is None and step_max is None:
            step_min = 30
            step_max = 180

        def fetch_fn(start, end):
            if self.download_history(start, end):
                return self.page.iter_transactions(account)
            return iter([])

        assert step_max <= 365*2  # PayPal limitations as of 2014-06-16
        for i in self.smart_fetch(beginning=self.BEGINNING,
                                  end=datetime.date.today(),
                                  step_min=step_min,
                                  step_max=step_max,
                                  fetch_fn=fetch_fn):
            yield i

    def smart_fetch(self, beginning, end, step_min, step_max, fetch_fn):
        """
        Fetches transactions in small chunks to avoid request timeouts.
        Time period of each requested chunk is adjusted dynamically.
        """
        FACTOR = 2
        step = step_min
        while end > beginning:
            start = end - datetime.timedelta(step)
            chunk = list(fetch_fn(start, end))
            end = start - datetime.timedelta(1)
            if len(chunk) > 50:
                # If there're too much transactions in current period, decrease
                # the period.
                step = max(step_min, step/FACTOR)
            else:
                # If there's no transactions, or only a bit, in current period,
                # increase the period.
                step = min(step_max, step*FACTOR)
            for trans in chunk:
                yield trans

    def download_history(self, start, end):
        """
        Download history.
        However, it is not normalized, and sometimes the download is refused
        and sent later by mail.
        """
        s = start.strftime('%d/%m/%Y')
        e = end.strftime('%d/%m/%Y')
        # Settings a big magic number so we hope to get all transactions for the period
        LIMIT = '9999'
        if self.account_type == "pro":
            self.location('https://www.paypal.com/webapps/business/activity?fromdate=' + s + '&todate=' + e + '&transactiontype=ALL_TRANSACTIONS&currency=ALL_TRANSACTIONS_CURRENCY&limit=' + LIMIT)
        else:
            self.location('https://www.paypal.com/myaccount/activity/filter?typeFilter=all&isNewSearch=true&startDate=' + s + '&endDate=' + e + '&limit=' + LIMIT)
        return self.page.transaction_left()

    def transfer(self, from_id, to_id, amount, reason=None):
        raise NotImplementedError()

    def convert_amount(self, account, trans):
        if trans['actions']['details']['action'] == 'ACTIVITY_DETAILS':
            self.location(trans['actions']['details']['url'])
        if self.is_on_page(HistoryDetailsPage):
            cc = self.page.get_converted_amount(account)
            if cc:
                trans['originalAmount'] = trans['netAmount']
                trans['netAmount'] = cc

        return trans

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


from weboob.capabilities.bank import Account, AccountNotFound, Transaction
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.capabilities.bank.transactions import \
    AmericanTransaction as AmTr

from .parser import StatementParser, clean_label

from time import sleep
from tempfile import mkdtemp
from shutil import rmtree
from itertools import chain
import datetime
import re
import os
import subprocess


__all__ = ['Citibank']


def retrying(func):
    def inner(*args, **kwargs):
        MAX_RETRIES = 10
        MAX_DELAY = 10
        for i in xrange(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OnceAgain:
                sleep(min(1 << i, MAX_DELAY))
        raise BrowserUnavailable('Unexpected site behavior. '
                                 'Perhaps this module needs some fixing...')
    return inner


class OnceAgain(Exception):
    pass


class Citibank(object):
    """
    Citibank website uses lots of Javascript, some of which seems to be
    dynamically generated and intentionally obfuscated.
    Our answer to THAT is... heavy artillery firing Selenium rounds!

    External dependencies:
    Firefox (https://www.mozilla.org/firefox).
    MuPDF (http://www.mupdf.com).
    Python bindings for Selenium (https://pypi.python.org/pypi/selenium).
    Xvfb (http://www.x.org/releases/X11R7.6/doc/man/man1/Xvfb.1.xhtml).

    Tested on Arch Linux snapshot of 2014-08-25 (official and user packages).
    Don't forget to do "export DISPLAY=:0".

    Only a single credit card account is currently supported.
    Contributions are welcome!
    """

    def __init__(self, username, password, logger, **kwargs):
        self._logger = logger
        self._username = username
        self._password = password

    def get_account(self, id_):
        account = next(self.iter_accounts())
        if account.id != id_:
            raise AccountNotFound()
        return account

    def iter_accounts(self):
        self.start()
        bal = self.wait('div.cT-valueItem span.cT-balanceIndicator1')[0].text
        account = Account()
        account.id = self._account_id()
        account.label = self._account_link().text
        account.currency = Account.get_currency(bal)
        account.balance = -AmTr.decimal_amount(bal)
        account.type = Account.TYPE_CARD
        self.finish()
        yield account

    def iter_history(self, account):
        for trans in chain(self.iter_history_recent(account),
                           self.iter_history_statements(account)):
            yield trans

    def start(self):
        # To avoid ImportError during e.g. building modules list.
        from selenium import webdriver

        HOME_URL = 'https://online.citibank.com/US/JPS/portal/Home.do'
        WIDTH = 1920
        HEIGHT = 10000  # So that everything fits...

        self._downloads = mkdtemp()
        self._logger.debug('Saving downloaded files to %s' % self._downloads)
        prof = webdriver.FirefoxProfile()
        prof.set_preference('browser.download.folderList', 2)
        prof.set_preference('browser.download.dir', self._downloads)
        prof.set_preference('browser.helperApps.neverAsk.saveToDisk',
                            'application/pdf')
        prof.set_preference('pdfjs.disabled', True)
        self._browser = webdriver.Firefox(prof)
        self._browser.set_window_size(WIDTH, HEIGHT)

        self._browser.get('https://online.citibank.com')
        self.wait('input[name="usernameMasked"]')[0].send_keys(self._username)
        self.wait('input[name="password"]')[0].send_keys(self._password)
        self.wait('form[name="SignonForm"]')[0].submit()
        self._browser.get(HOME_URL)
        if self._browser.current_url != HOME_URL:
            raise BrowserIncorrectPassword()

    def finish(self):
        prof_dir = self._browser.firefox_profile.profile_dir
        self._browser.close()
        del self._browser
        rmtree(self._downloads)
        del self._downloads
        rmtree(prof_dir)

    def iter_history_recent(self, account):
        self.start()
        if account.id != self._account_id():
            raise AccountNotFound()
        self._account_link().click()
        self.wait_ajax()
        for span in self.find('span.cM-maximizeButton'):
            span.click()
        for tr in self.find('tr.payments,tr.purchase'):
            trdata = lambda n: tr.find_element_by_css_selector(
                        'td.cT-bodyTableColumn%i span.cT-line1' % n).text
            treid = tr.get_attribute('id').replace('rowID', 'rowIDExt')
            tredata = {}
            for tre in self.find('tr#%s' % treid):
                labels = [x.text for x in tre.find_elements_by_css_selector(
                                                    'div.cT-labelItem')]
                values = [x.text for x in tre.find_elements_by_css_selector(
                                                    'div.cT-valueItem')]
                tredata = dict(zip(labels, values))

            ref = tredata.get(u'Reference Number:', u'')
            tdate = trdata(1)
            pdate = tredata.get(u'Posted Date :', tdate)
            desc = clean_label(trdata(2))
            amount = trdata(4)

            tdate = datetime.datetime.strptime(tdate, '%m-%d-%Y')
            pdate = datetime.datetime.strptime(pdate, '%m-%d-%Y')

            if amount.startswith(u'(') and amount.endswith(u')'):
                amount = AmTr.decimal_amount(amount[1:-1])
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

        self.finish()

    def iter_history_statements(self, account):
        # To avoid ImportError during e.g. building modules list.
        from selenium.webdriver.common.keys import Keys
        from selenium.common.exceptions import MoveTargetOutOfBoundsException,\
                                               ElementNotVisibleException
        self.start()
        if account.id != self._account_id():
            raise AccountNotFound()
        self.wait('a#cmlink_ViewPastStmtLink')[0].click()
        opts = self.wait('option#currentStatementDateOptions')
        for i, opt in enumerate(opts):
            # We're interested only in finalized statements.
            if u'Unbilled' in opt.get_attribute('value'):
                continue
            self.wait('div#currentStatementsDate-button')[0].click()
            ul = self.wait('ul#currentStatementsDate-menu')[0]
            while True:
                try:
                    self.wait('li#currentStatementDateOptions span')[i].click()
                    break
                except (MoveTargetOutOfBoundsException,
                        ElementNotVisibleException):
                    ul.send_keys(Keys.ARROW_DOWN)
            self.wait('a#downloadCurrentStatements')[0].click()
            pdfname = self.wait_file('.pdf')
            pdfpath = os.path.join(self._downloads, pdfname)
            with open(pdfpath, 'rb') as f:
                parser = StatementParser(f.read())
            os.remove(pdfpath)
            # Transactions in a statement can go in different order.
            ts = sorted(parser.read_transactions(),
                        cmp=lambda t1, t2: cmp(t2.date, t1.date))
            for t in ts:
                yield t
        self.finish()

    def find(self, selector):
        self._logger.debug('Finding selector """%s""" on page %s' % (
            selector, self._browser.current_url))
        return self._browser.find_elements_by_css_selector(selector)

    @retrying
    def wait(self, selector):
        els = self.find(selector)
        if not els:
            raise OnceAgain()
        return els

    @retrying
    def wait_ajax(self):
        self._logger.debug('Waiting for async requests to finish on page %s'
            % self._browser.current_url)
        els = self._browser.find_elements_by_xpath(
            u'//*[contains(text(),"Please wait")]')
        if not els or any(x.is_displayed() for x in els):
            raise OnceAgain()

    @retrying
    def wait_file(self, suffix):
        self._logger.debug('Waiting for file "*%s" to finish downloading.' %
            suffix)
        for name in os.listdir(self._downloads):
            if not name.endswith(suffix):
                continue
            path = os.path.join(self._downloads, name)
            # Wait until file is not empty.
            if not os.stat(path).st_size:
                continue
            # Wait until no processes are accessing the file.
            if subprocess.call(['fuser', '-s', path]) == 0:
                continue
            return name
        raise OnceAgain()

    def _account_link(self):
        return self.wait('a#cmlink_AccountNameLink')[0]

    def _account_id(self):
        return re.match('.*-([0-9]+)$', self._account_link().text).group(1)

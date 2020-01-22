# -*- coding: utf-8 -*-

# Copyright(C) 2015 Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import shutil
import tempfile
import time
from datetime import date

from weboob.browser import URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.browser.selenium import (
    SeleniumBrowser, webdriver, AnyCondition, VisibleXPath, IsHereCondition,
    FakeResponse,
)

from .ent_pages import (
    LoginPage, AccueilPage, AccountsPage, HistoryPage,
    AccountsXlsPage, HistoryXlsPage,
)


class SogecarteEntrepriseBrowser(SeleniumBrowser):
    BASEURL = 'https://www.sogecartenet.fr'

    # Required so the input for the transaction history date list do not overlap vertically
    WINDOW_SIZE = (1920, 1080)

    # False for debug / True for production
    HEADLESS = True

    DRIVER = webdriver.Chrome

    login = URL(r'/gestionnaire-ihm/SOCGEN/FRA', LoginPage)
    accueil = URL(r'/gestionnaire-ihm/SOCGEN/FRA#!ACCUEIL', AccueilPage)
    account_list = URL(r'/gestionnaire-ihm/SOCGEN/FRA#!GESTION_PARC_CARTES', AccountsPage)
    history = URL(r'/gestionnaire-ihm/SOCGEN/FRA#!DEPENSES_ENTREPRISE', HistoryPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        # Safe way to create a temporary folder.
        self.dl_folder = tempfile.mkdtemp()
        kwargs['preferences'] = {
            'download.default_directory': self.dl_folder,
        }
        super(SogecarteEntrepriseBrowser, self).__init__(*args, **kwargs)
        # This is to avoid errors if the day changes while parsing.
        self.today = date.today()
        self.selected_account = None

    def deinit(self):
        super(SogecarteEntrepriseBrowser, self).deinit()
        shutil.rmtree(self.dl_folder)

    def do_login(self):
        self.login.go()
        self.wait_until_is_here(self.login)

        self.page.login(self.username, self.password)

        self.wait_until(AnyCondition(
            IsHereCondition(self.accueil),
            VisibleXPath('//div[contains(@class, "Notification-error-message")]'),
        ))

        if not self.accueil.is_here():
            assert self.login.is_here(), 'We landed on an unknown page'
            error = self.page.get_error()
            if any((
                'Votre compte a été désactivé' in error,
                'Votre compte est bloqué' in error,
            )):
                raise ActionNeeded(error)
            raise BrowserIncorrectPassword(error)

    def find_file_path(self, prefix, suffix):
        # We don't know the name of the file, but we know the folder.
        # The folder is empty (since we delete every file after using them),
        # so we just try to find all files in that folder and we are going to find only one.
        file_path = ''
        for file in os.listdir(self.dl_folder):
            if file.endswith(suffix) and file.startswith(prefix):
                file_path = os.path.join(self.dl_folder, file)
                break
        return file_path

    def retry_find_file_path(self, prefix, suffix):
        start = time.time()
        # Try to find the new file every 0.5s, faster and safer than waiting
        # a fixed amount of time after downloading the file.
        while time.time() < start + 30.0:
            path = self.find_file_path(prefix, suffix)
            if path:
                return path
            time.sleep(0.5)

    @need_login
    def iter_accounts(self):
        self.account_list.stay_or_go()
        self.wait_until_is_here(self.account_list)

        # This download the file with the list of all accounts in a `.xls`
        self.page.download_accounts()

        file_path = self.retry_find_file_path('details_carte', '.xls')
        assert file_path, 'Could not find the downloaded file'

        # We can't force change the SeleniumBrowser's page (self.page = ...)
        page = AccountsXlsPage(self, file_path, FakeResponse(
            url=self.url,
            text='',
            content=b'',
            encoding='latin-1',
        ))

        for acc in page.iter_accounts():
            yield acc

        os.remove(file_path)

    @need_login
    def iter_transactions(self, account, coming=False):
        self.history.go()

        self.wait_until_is_here(self.history)
        self.page.go_transactions_list_tab()

        if not self.selected_account or self.selected_account != account.id:
            # The input with the information of the selected account can't
            # be parsed. So we have to manually track of which account is
            # selected to avoid re-select the same account and loose time.
            self.page.select_account(account)
            self.selected_account = account.id

        if self.page.download_transactions():
            file_path = self.retry_find_file_path('requete_cumul', '.xls')
            assert file_path, 'Could not find the downloaded file'

            # We can't force change the SeleniumBrowser's page (self.page = ...)
            page = HistoryXlsPage(self, file_path, FakeResponse(
                url=self.url,
                text='',
                content=b'',
                encoding='latin-1',
            ))

            for tr in sorted_transactions(page.iter_history()):
                if tr.date >= self.today and coming:
                    yield tr
                elif tr.date < self.today and not coming:
                    yield tr

            os.remove(file_path)

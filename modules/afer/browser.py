# -*- coding: utf-8 -*-

# Copyright(C) 2015      James GALT
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

from random import randint
from weboob.browser import URL, LoginBrowser, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.compat import basestring

from .pages import LoginPage, IndexPage, BadLogin, AccountDetailPage, AccountHistoryPage


class AferBrowser(LoginBrowser):
    BASEURL = 'https://adherent.gie-afer.fr'

    login = URL('/web/ega.nsf/listeAdhesions\?OpenForm', LoginPage)
    bad_login = URL('/names.nsf\?Login', BadLogin)
    index = URL('/web/ega.nsf/listeAdhesions\?OpenForm', IndexPage)
    account_detail = URL('/web/ega.nsf/soldeEpargne\?openForm', AccountDetailPage)
    account_history = URL('/web/ega.nsf/generationSearchModule\?OpenAgent', AccountHistoryPage)
    history_detail = URL('/web/ega.nsf/WOpendetailOperation\?OpenAgent', AccountHistoryPage)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.go()

        try:
            self.page.login(self.username, self.password)
        except BrowserUnavailable:
            raise BrowserIncorrectPassword()

        if self.bad_login.is_here():
            error = self.page.get_error()
            if "La saisie de l’identifiant ou du code confidentiel est incorrecte" in error or \
               "Veuillez-vous identifier" in error:
                raise BrowserIncorrectPassword(error)
            else:
                assert False, "Message d'erreur inconnu: %s" % error


    @need_login
    def iter_accounts(self):
        self.index.stay_or_go()
        return self.page.iter_accounts()

    @need_login
    def iter_investment(self, account):
        self.account_detail.go(params={'nads': account.id})
        return self.page.iter_investment()

    @need_login
    def iter_history(self, account):
        al = randint(0, 1000)
        data = {'cdeAdh': account.id, 'al': al, 'page': 1, 'form': 'F'}
        self.account_history.go(data={'cdeAdh': account.id, 'al': al, 'page': 1, 'form': 'F'})
        return self.page.iter_history(data=data)

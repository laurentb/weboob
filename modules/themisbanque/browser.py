# -*- coding: utf-8 -*-

# Copyright(C) 2015      Romain Bignon
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


from weboob.browser import LoginBrowser, URL, need_login

from .pages import LoginPage, LoginConfirmPage, AccountsPage, HistoryPage


class ThemisBrowser(LoginBrowser):
    BASEURL = 'https://esab.themisbanque.eu/'

    home = URL('/es@b/fr/esab.jsp')
    login = URL('/es@b/fr/codeident.jsp', LoginPage)
    login_confirm = URL('/es@b/servlet/internet0.ressourceWeb.servlet.Login', LoginConfirmPage)
    accounts = URL(r'/es@b/servlet/internet0.ressourceWeb.servlet.PremierePageServlet\?pageToTreatError=fr/Infos.jsp&dummyDate=', AccountsPage)
    history = URL('/es@b/servlet/internet0.ressourceWeb.servlet.ListeDesMouvementsServlet.*', HistoryPage)

    def do_login(self):
        self.home.go()
        self.login.go()
        self.page.login(self.username, self.password)

    @need_login
    def iter_accounts(self):
        self.accounts.stay_or_go()
        return self.page.iter_accounts()

    @need_login
    def get_history(self, account):
        self.location(account._link)
        return self.page.get_operations()

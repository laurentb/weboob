# -*- coding: utf-8 -*-

# Copyright(C) 2018      Phyks (Lucas Verney)
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

from __future__ import unicode_literals

import itertools


from weboob.browser import LoginBrowser, need_login, URL
from weboob.exceptions import BrowserIncorrectPassword

from .pages import BillsPage, DocumentsPage, LoginPage


class EkwateurBrowser(LoginBrowser):
    BASEURL = 'https://mon-espace.ekwateur.fr/'

    login_page = URL('/se_connecter', LoginPage)
    bills_page = URL('/mes_factures_et_acomptes', BillsPage)
    documents_page = URL('/documents', DocumentsPage)

    def do_login(self):
        self.login_page.go().do_login(self.username, self.password)
        self.bills_page.stay_or_go()
        if not self.bills_page.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_subscriptions(self):
        return self.bills_page.stay_or_go().get_subscriptions()

    @need_login
    def iter_documents(self, sub_id):
        return itertools.chain(
            self.documents_page.stay_or_go().get_documents(sub_id=sub_id),
            self.documents_page.stay_or_go().get_cgv(sub_id),
            self.documents_page.stay_or_go().get_justificatif(sub_id),
            self.bills_page.stay_or_go().get_bills(sub_id=sub_id)
        )

# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, CaptchaPage, ProfilPage, DocumentsPage, DocumentsDetailsPage


class MaterielnetBrowser(LoginBrowser):
    BASEURL = 'https://secure.materiel.net'

    login = URL(r'https://www.materiel.net/form/login',
                r'/Login/PartialPublicLogin', LoginPage)
    captcha = URL('/pm/client/captcha.html', CaptchaPage)
    profil = URL(r'/Account/InformationsSection', ProfilPage)
    documents = URL(r'/Orders/PartialCompletedOrdersHeader', DocumentsPage)
    document_details = URL(r'/Orders/PartialCompletedOrderContent', DocumentsDetailsPage)

    def do_login(self):
        self.login.go()
        self.page.login(self.username, self.password)

        if self.captcha.is_here():
            BrowserIncorrectPassword()

        if self.login.is_here():
            error = self.page.get_error()
            # when everything is good we land on this page
            if error:
                raise BrowserIncorrectPassword(error)

    @need_login
    def get_subscription_list(self):
        return self.profil.stay_or_go().get_list()

    @need_login
    def iter_documents(self, subscription):
        json_response = self.location('/Orders/CompletedOrdersPeriodSelection').json()

        for data in json_response:
            return self.documents.go(data=data).get_documents()

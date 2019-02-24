# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, CaptchaPage, ProfilPage, DocumentsPage, DocumentsDetailsPage


class MaterielnetBrowser(LoginBrowser):
    BASEURL = 'https://secure.materiel.net'

    login = URL(r'/Login/Login', LoginPage)
    captcha = URL('/pm/client/captcha.html', CaptchaPage)
    profil = URL(r'/Account/InformationsSection',
                 r'/pro/Account/InformationsSection', ProfilPage)
    documents = URL(r'/Orders/PartialCompletedOrdersHeader',
                    r'/pro/Orders/PartialCompletedOrdersHeader', DocumentsPage)
    document_details = URL(r'/Orders/PartialCompletedOrderContent',
                           r'/pro/Orders/PartialCompletedOrderContent', DocumentsDetailsPage)

    def __init__(self, *args, **kwargs):
        super(MaterielnetBrowser, self).__init__(*args, **kwargs)
        self.is_pro = None

    def par_or_pro_location(self, url, *args, **kwargs):
        if self.is_pro:
            url = '/pro' + url

        return super(MaterielnetBrowser, self).location(url, *args, **kwargs)

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

        self.is_pro = 'pro' in self.url

    @need_login
    def get_subscription_list(self):
        return self.par_or_pro_location('/Account/InformationsSection').page.get_list()

    @need_login
    def iter_documents(self, subscription):
        json_response = self.par_or_pro_location('/Orders/CompletedOrdersPeriodSelection').json()

        for data in json_response:
            for doc in self.par_or_pro_location('/Orders/PartialCompletedOrdersHeader', data=data).page.get_documents():
                yield doc

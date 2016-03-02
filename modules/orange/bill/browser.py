# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Vincent Paredes
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
from .pages import LoginPage, ProfilPage, BillsPage

__all__ = ['OrangeBillBrowser']


class OrangeBillBrowser(LoginBrowser):
    loginpage = URL('https://id.orange.fr/auth_user/bin/auth_user.cgi', LoginPage)
    profilpage = URL('https://espaceclientv3.orange.fr/\?page=profil-infosPerso', ProfilPage)
    billspage = URL('https://m.espaceclientv3.orange.fr/\?page=factures-archives',
                    'https://.*.espaceclientv3.orange.fr/\?page=factures-archives',
                    'https://espaceclientv3.orange.fr/\?page=factures-archives',
                     BillsPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.loginpage.stay_or_go().login(self.username, self.password)

        self.billspage.go()
        if self.loginpage.is_here():
            raise BrowserIncorrectPassword()

    def get_nb_remaining_free_sms(self):
        raise NotImplementedError()

    def post_message(self, message, sender):
        raise NotImplementedError()

    @need_login
    def get_subscription_list(self):
        return self.billspage.stay_or_go().get_list()

    @need_login
    def iter_documents(self, subscription):
        return self.billspage.stay_or_go().get_documents(subid=subscription.id)

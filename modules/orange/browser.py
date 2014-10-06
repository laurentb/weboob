# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


#~ from .pages.compose import ClosePage, ComposePage, ConfirmPage, SentPage
#~ from .pages.login import LoginPage

from .pages import LoginPage, ComposePage, ConfirmPage

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword


__all__ = ['OrangeBrowser']


class OrangeBrowser(Browser):
    DOMAIN = 'orange.fr'
    PAGES = {
        'http://id.orange.fr/auth_user/bin/auth_user.cgi.*': LoginPage,
        'http://id.orange.fr/auth_user/bin/auth0user.cgi.*': LoginPage,
        'http://smsmms1.orange.fr/./Sms/sms_write.php.*'   : ComposePage,
        'http://smsmms1.orange.fr/./Sms/sms_write.php?command=send' : ConfirmPage,
        }

    def get_nb_remaining_free_sms(self):
        self.location("http://smsmms1.orange.fr/M/Sms/sms_write.php")
        return self.page.get_nb_remaining_free_sms()

    def home(self):
        self.location("http://smsmms1.orange.fr/M/Sms/sms_write.php")

    def is_logged(self):
        self.location("http://smsmms1.orange.fr/M/Sms/sms_write.php", no_login=True)
        return not self.is_on_page(LoginPage)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.location('http://id.orange.fr/auth_user/bin/auth_user.cgi?url=http://www.orange.fr', no_login=True)
        self.page.login(self.username, self.password)
        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def post_message(self, message, sender):
        if not self.is_on_page(ComposePage):
            self.home()
        self.page.post_message(message, sender)

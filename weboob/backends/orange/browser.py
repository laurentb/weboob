# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


#~ from .pages.compose import ClosePage, ComposePage, ConfirmPage, SentPage
#~ from .pages.login import LoginPage

from .pages import LoginPage, ComposePage, ConfirmPage

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword


__all__ = ['OrangeBrowser']


class OrangeBrowser(BaseBrowser):
    DOMAIN = 'orange.fr'
    PAGES = {
        'http://id.orange.fr/auth_user/bin/auth_user.cgi.*': LoginPage,
        'http://id.orange.fr/auth_user/bin/auth0user.cgi.*': LoginPage,
        'http://smsmms1.orange.fr/M/Sms/sms_write.php.*'   : ComposePage,
        'http://smsmms1.orange.fr/M/Sms/sms_write.php?command=send' : ConfirmPage,
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

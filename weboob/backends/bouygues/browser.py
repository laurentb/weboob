# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


from .pages.compose import ComposeFrame, ComposePage, ConfirmPage, SentPage
from .pages.login import LoginPage, LoginSASPage

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword


__all__ = ['BouyguesBrowser']


class BouyguesBrowser(BaseBrowser):
    DOMAIN = 'www.bouyguestelecom.fr'
    PAGES = {
        'http://www.espaceclient.bouyguestelecom.fr/ECF/jsf/client/envoiSMS/viewEnvoiSMS.jsf': ComposePage,
        'http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/sendSMS.phtml': ComposeFrame,
        'http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/confirmSendSMS.phtml': ConfirmPage,
        'https://www.espaceclient.bouyguestelecom.fr/ECF/jsf/submitLogin.jsf': LoginPage,
        'https://www.espaceclient.bouyguestelecom.fr/ECF/SasUnifie': LoginSASPage,
        'http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/resultSendSMS.phtml': SentPage,
        }

    def home(self):
        self.location('http://www.espaceclient.bouyguestelecom.fr/ECF/jsf/client/envoiSMS/viewEnvoiSMS.jsf')

    def is_logged(self):
        return 'code' not in [form.name for form in self.forms()]

    def login(self):
        self.location('https://www.espaceclient.bouyguestelecom.fr/ECF/jsf/submitLogin.jsf', no_login=True)
        self.page.login(self.username, self.password)
        assert self.is_on_page(LoginSASPage)
        self.page.login()
        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def post_message(self, message):
        if not self.is_on_page(ComposeFrame):
            self.home()
            self.location('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/sendSMS.phtml')
        self.page.post_message(message)
        assert self.is_on_page(ConfirmPage)
        self.page.confirm()
        assert self.is_on_page(SentPage)

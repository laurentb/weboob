# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


from weboob.tools.compat import quote_plus

from .pages.compose import ClosePage, ComposePage, ConfirmPage, SentPage
from .pages.login import LoginPage

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword


__all__ = ['SfrBrowser']


class SfrBrowser(Browser):
    DOMAIN = 'www.sfr.fr'
    PAGES = {
        'http://messagerie-.+.sfr.fr/webmail/close_xms_tab.html': ClosePage,
        'http://www.sfr.fr/xmscomposer/index.html\?todo=compose': ComposePage,
        'http://www.sfr.fr/xmscomposer/mc/envoyer-texto-mms/confirm.html': ConfirmPage,
        'https://www.sfr.fr/cas/login\?service=.*': LoginPage,
        'http://www.sfr.fr/xmscomposer/mc/envoyer-texto-mms/send.html': SentPage,
        }

    def get_nb_remaining_free_sms(self):
        if not self.is_on_page(ComposePage):
            self.home()
        return self.page.get_nb_remaining_free_sms()

    def home(self):
        self.location('http://www.sfr.fr/xmscomposer/index.html?todo=compose')

    def is_logged(self):
        return 'loginForm' not in [form.name for form in self.forms()]

    def login(self):
        service_url = 'http://www.sfr.fr/xmscomposer/j_spring_cas_security_check'
        self.location('https://www.sfr.fr/cas/login?service=%s' % quote_plus(service_url), no_login=True)
        self.page.login(self.username, self.password)
        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def post_message(self, message):
        if not self.is_on_page(ComposePage):
            self.home()
        self.page.post_message(message)
        if self.is_on_page(ConfirmPage):
            self.page.confirm()
        assert self.is_on_page(ClosePage) or self.is_on_page(SentPage)

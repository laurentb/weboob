# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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

from weboob.browser.pages import HTMLPage
from weboob.browser.filters.html import Attr
from weboob.browser.filters.standard import CleanText
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        msg = CleanText(".//*[@id='message_client']/text()")(self.doc)

        if "maintenance" in msg:
            raise BrowserUnavailable(msg)

        form = self.get_form(name="acces_identification")
        form['login'] = login
        form['passwd'] = passwd
        # With form submit and allow_redirects=False
        # self.response is associated with precedent request
        # so we need to store the submit response
        submit_page = form.submit(allow_redirects=False)

        if submit_page.headers.get('X-Arkea-sca') == '1':
            # User needs to validate its 2FA
            self.browser.check_interactive()
        self.browser.location(submit_page.headers['Location'])

    def check_is_blocked(self):
        error_message = CleanText('//div[@id="acces_client"]//p[@class="container error"]/label')(self.doc)
        if 'Votre accès est désormais bloqué' in error_message:
            raise ActionNeeded(error_message)


class TwoFaPage(HTMLPage):
    def is_here(self):
        # Handle 90 days 2FA and Secure access
        return 'Sécurité renforcée tous les 90 jours' in CleanText('//div[@id="titre_page"]/h1')(self.doc)

    def get_sms_form(self):
        sms_form = self.get_form()
        sms_form['numeroSelectionne.value'] = Attr(
            '//div[@id="div_secu_forte_otp"]/input[@name="numeroSelectionne.value"]',
            'value'
        )(self.doc)
        return sms_form

    def check_otp_error_message(self):
        error_message = CleanText('//span/label[@class="error"]')(self.doc)
        if 'Le code saisi est incorrect' in error_message:
            raise BrowserIncorrectPassword()
        assert not error_message, 'Error during otp validation: %s' % error_message


class UnavailablePage(HTMLPage):
    def on_load(self):
        raise BrowserUnavailable(CleanText('//h2[@class="titre"]')(self.doc))

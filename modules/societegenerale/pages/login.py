# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


from logging import error
import re
from weboob.tools.json import json

from weboob.tools.browser import BrowserUnavailable
from weboob.tools.mech import ClientForm

from .base import BasePage
from ..captcha import Captcha, TileError


__all__ = ['LoginPage', 'BadLoginPage']


class LoginPage(BasePage):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def login(self, login, password):
        DOMAIN_LOGIN = self.browser.DOMAIN_LOGIN
        DOMAIN = self.browser.DOMAIN

        url_login = 'https://' + DOMAIN_LOGIN + '/index.html'

        base_url = 'https://' + DOMAIN
        url = base_url + '//sec/vk/gen_crypto?estSession=0'
        headers = {
                 'Referer': url_login
                  }
        request = self.browser.request_class(url, None, headers)
        infos_data = self.browser.readurl(request)

        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)

        infos = json.loads(infos_data.replace("'", '"'))

        url = base_url + '//sec/vk/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]
        img = Captcha(self.browser.openurl(url), infos)

        try:
            img.build_tiles()
        except TileError as err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        self.browser.select_form('n2g_authentification')
        self.browser.controls.append(ClientForm.TextControl('text', 'codsec', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'cryptocvcs', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'vk_op', {'value': 'auth'}))
        self.browser.set_all_readonly(False)

        self.browser['codcli'] = login
        self.browser['user_id'] = login
        self.browser['codsec'] = img.get_codes(password[:6])
        self.browser['cryptocvcs'] = infos["crypto"]
        self.browser.form.action = 'https://particuliers.secure.societegenerale.fr//acces/authlgn.html'
        self.browser.submit(nologin=True)


class BadLoginPage(BasePage):
    pass

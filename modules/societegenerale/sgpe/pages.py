# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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
from decimal import Decimal

from weboob.tools.browser import BasePage
from weboob.tools.json import json
from weboob.tools.mech import ClientForm
from weboob.tools.misc import to_unicode

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

from ..captcha import Captcha, TileError


__all__ = ['LoginPage', 'AccountsPage']


class SGPEPage(BasePage):
    def get_error(self):
        err = self.document.getroot().cssselect('div.ngo_mire_reco_message') \
            or self.document.getroot().cssselect('#nge_zone_centre .nge_cadre_message_utilisateur')
        if err:
            return err[0].text.strip()


class LoginPage(SGPEPage):
    def login(self, login, password):
        DOMAIN = self.browser.DOMAIN

        url_login = 'https://' + DOMAIN + '/'

        base_url = 'https://' + DOMAIN
        url = base_url + '//sec/vk/gen_crypto?estSession=0'
        headers = {'Referer': url_login}
        request = self.browser.request_class(url, None, headers)
        infos_data = self.browser.readurl(request)

        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)

        infos = json.loads(infos_data.replace("'", '"'))

        url = base_url + '//sec/vk/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]

        self.browser.readurl(url)
        img = Captcha(self.browser.openurl(url), infos)

        try:
            img.build_tiles()
        except TileError, err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        self.browser.select_form(self.browser.LOGIN_FORM)
        self.browser.controls.append(ClientForm.TextControl('text', 'codsec', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'cryptocvcs', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'vk_op', {'value': 'auth'}))
        self.browser.set_all_readonly(False)

        self.browser['user_id'] = login.encode(self.browser.ENCODING)
        self.browser['codsec'] = img.get_codes(password[:6])
        self.browser['cryptocvcs'] = infos["crypto"]
        self.browser.form.action = base_url + '/authent.html'
        self.browser.submit(nologin=True)


class AccountsPage(SGPEPage):
    def get_list(self):
        table = self.parser.select(self.document.getroot(), '#tab-corps', 1)
        for tr in self.parser.select(table, 'tr', 'many'):
            tdname, tdid, tdagency, tdbalance = [td.text_content().strip()
                                                 for td
                                                 in self.parser.select(tr, 'td', 4)]
            # it has empty rows - ignore those without the necessary info
            if all((tdname, tdid, tdbalance)):
                account = Account()
                account.label = to_unicode(tdname)
                account.id = to_unicode(tdid.replace(u'\xa0', '').replace(' ', ''))
                account._agency = to_unicode(tdagency)
                account.balance = Decimal(FrenchTransaction.clean_amount(tdbalance))
                account.currency = account.get_currency(tdbalance)
                yield account

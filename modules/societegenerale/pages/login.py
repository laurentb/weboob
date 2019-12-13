# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


from io import BytesIO
from base64 import b64decode
from logging import error
import re
from weboob.tools.json import json

from weboob.exceptions import BrowserUnavailable, BrowserPasswordExpired, ActionNeeded
from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.filters.standard import CleanText
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import AddRecipientBankError

from .base import BasePage
from ..captcha import Captcha, TileError


class PasswordPage(object):
    STRANGE_KEY = ["180","149","244","125","115","058","017","071","075","119","167","040","066","083","254","151","212","245","193","224","006","068","139","054","089","083","111","208","105","235","109","030","130","226","155","245","157","044","061","233","036","101","145","103","185","017","126","142","007","192","239","140","133","250","194","222","079","178","048","184","158","158","086","160","001","114","022","158","030","210","008","067","056","026","042","113","043","169","128","051","107","112","063","240","108","003","079","059","053","127","116","084","157","203","244","031","062","012","062","093"]
    strange_map = None

    def decode_grid(self, infos):
        grid = infos['grid']
        if isinstance(infos['grid'], list):
            grid = infos['grid'][0]
        grid = b64decode(grid).decode('ascii')
        grid = [int(x) for x in re.findall('[0-9]{3}', grid)]
        n = int(infos['nbrows']) * int(infos['nbcols'])

        self.strange_map = list(grid[:n])
        grid = list(grid[n:])
        new_grid = list(grid)

        s = n
        u = list(infos['crypto'])

        for j in range(s):
            u[j] = '%02d' % ord(u[j])
        for i in range(5, 0, -1):
            for j in range(s):
                new_grid[i*s+j] = '%03d' % (new_grid[i*s+j]^new_grid[(i-1)*s+j])
        for j in range(s):
            new_grid[j] = '%03d' % (new_grid[j]^int(self.STRANGE_KEY[j])^self.strange_map[j])
        for j in range(s):
            self.strange_map[j] = int(u[j])^self.strange_map[j]

        return new_grid


class MainPage(BasePage, PasswordPage):
    """
    be carefull : those differents methods and PREFIX_URL are used
    in another page of an another module which is an abstract of this page
    """
    PREFIX_URL = '//sec'

    def get_url(self, path):
        return (self.browser.BASEURL + self.PREFIX_URL + path)

    def get_authentication_infos(self):
        url = self.get_url('/vkm/gen_crypto?estSession=0')
        infos_data = self.browser.open(url).text
        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)
        infos = json.loads(infos_data.replace("'", '"'))
        return infos

    def get_authentication_data(self):
        infos = self.get_authentication_infos()

        infos['grid'] = self.decode_grid(infos)

        url = self.get_url('/vkm/gen_ui?modeClavier=0&cryptogramme=' + infos['crypto'])
        img = Captcha(BytesIO(self.browser.open(url).content), infos)

        try:
            img.build_tiles()
        except TileError as err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        return {
            'infos': infos,
            'img': img,
        }

    def login(self, login, password):
        authentication_data = self.get_authentication_data()

        pwd = authentication_data['img'].get_codes(password[:6])
        t = pwd.split(',')
        newpwd = ','.join(t[self.strange_map[j]] for j in range(6))

        data = {
            'top_code_etoile': 0,
            'top_ident': 1,
            'jeton': '',
            'cible': 300,
            'user_id': login.encode('iso-8859-1'),
            'codsec': newpwd,
            'cryptocvcs': authentication_data['infos']['crypto'].encode('iso-8859-1'),
            'vkm_op': 'auth',
        }
        self.browser.location(self.get_url('/vk/authent.json'), data=data)

    def handle_error(self):
        error_msg = CleanText('//span[@class="error_msg"]')(self.doc)
        if error_msg:
            # WARNING: this error occured during a recipient adding
            # I don't know if it can happen at another time
            raise AddRecipientBankError(message=error_msg)


class LoginPage(JsonPage):
    # statut, status...
    def get_reason(self):
        if Dict('commun/statut')(self.doc).lower() != 'ok':
            return Dict('commun/raison')(self.doc)

    def get_auth_method(self):
        data = Dict('chgtnivauth')(self.doc)
        if data['status'].lower() != 'ok':
            return

        auth_methods = []
        for auth_method in data['list_proc']:
            if not auth_method['unavailability_reason']:
                auth_methods.append(auth_method)

        # if we can't find any methods available we send the highest priority
        # so we can raise the right exception to the user
        auth_methods = auth_methods or data['list_proc']
        if auth_methods:
            return sorted(auth_methods, key=lambda k: k['priorite'])[0]


class BadLoginPage(BasePage):
    pass


class ReinitPasswordPage(BasePage):
    def on_load(self):
        raise BrowserPasswordExpired()


class ActionNeededPage(BasePage):
    # Mise à jour des conditions particulières de vos sonventions de comptes titres
    def on_load(self):
        raise ActionNeeded()


class ErrorPage(HTMLPage):
    def on_load(self):
        message = CleanText('//span[contains(text(), "Une erreur est survenue lors du chargement de la page")]')(self.doc)
        raise BrowserUnavailable(message)

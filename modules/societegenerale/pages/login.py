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


from base64 import b64decode
from logging import error
import re
from weboob.tools.json import json

from weboob.tools.browser import BrowserUnavailable
from weboob.tools.mech import ClientForm

from .base import BasePage
from ..captcha import Captcha, TileError


class LoginPage(BasePage):
    STRANGE_KEY = ["180","149","244","125","115","058","017","071","075","119","167","040","066","083","254","151","212","245","193","224","006","068","139","054","089","083","111","208","105","235","109","030","130","226","155","245","157","044","061","233","036","101","145","103","185","017","126","142","007","192","239","140","133","250","194","222","079","178","048","184","158","158","086","160","001","114","022","158","030","210","008","067","056","026","042","113","043","169","128","051","107","112","063","240","108","003","079","059","053","127","116","084","157","203","244","031","062","012","062","093"]
    strange_map = None

    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def decode_grid(self, infos):
        grid = b64decode(infos['grid'])
        grid = map(int, re.findall('[0-9]{3}', grid))
        n = int(infos['nbrows']) * int(infos['nbcols'])

        self.strange_map = list(grid[:n])
        grid = list(grid[n:])
        new_grid = list(grid)

        s = n
        u = list(infos['crypto'])

        for j in xrange(s):
            u[j] = '%02d' % ord(u[j])
        for i in xrange(5, 0, -1):
            for j in xrange(s):
                new_grid[i*s+j] = '%03d' % (new_grid[i*s+j]^new_grid[(i-1)*s+j])
        for j in xrange(s):
            new_grid[j] = '%03d' % (new_grid[j]^int(self.STRANGE_KEY[j])^self.strange_map[j])
        for j in xrange(s):
            self.strange_map[j] = int(u[j])^self.strange_map[j]

        return new_grid

    def login(self, login, password):
        DOMAIN_LOGIN = self.browser.DOMAIN_LOGIN
        DOMAIN = self.browser.DOMAIN

        url_login = 'https://' + DOMAIN_LOGIN + '/index.html'

        base_url = 'https://' + DOMAIN
        url = base_url + '//sec/vkm/gen_crypto?estSession=0'
        headers = {
                 'Referer': url_login
                  }
        request = self.browser.request_class(url, None, headers)
        infos_data = self.browser.readurl(request)

        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)

        infos = json.loads(infos_data.replace("'", '"'))

        infos['grid'] = self.decode_grid(infos)

        url = base_url + '//sec/vkm/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]
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
        self.browser.controls.append(ClientForm.TextControl('text', 'vkm_op', {'value': 'auth'}))
        self.browser.set_all_readonly(False)

        pwd = img.get_codes(password[:6])
        t = pwd.split(',')
        newpwd = ','.join([t[self.strange_map[j]] for j in xrange(6)])

        self.browser['codcli'] = login.encode('iso-8859-1')
        self.browser['user_id'] = login.encode('iso-8859-1')
        self.browser['codsec'] = newpwd
        self.browser['cryptocvcs'] = infos["crypto"].encode('iso-8859-1')
        self.browser.form.action = 'https://particuliers.secure.societegenerale.fr//acces/authlgn.html'
        self.browser.submit(nologin=True)


class BadLoginPage(BasePage):
    pass

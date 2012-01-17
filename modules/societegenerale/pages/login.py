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

from weboob.tools.browser import BasePage, BrowserUnavailable
from ..captcha import Captcha, TileError
from lxml import etree


__all__ = ['LoginPage']


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
        url = base_url + '/cvcsgenclavier?mode=jsom&estSession=0'
        headers = {
                 'Referer': url_login
                  }
        request = self.browser.request_class(url, None, headers)
        infos_data = self.browser.readurl(request)
        infos_xml = etree.XML(infos_data)
        infos = {}
        for el in ("cryptogramme", "nblignes", "nbcolonnes"):
          infos[el] = infos_xml.find(el).text

        infos["grille"] = ""
        for g in infos_xml.findall("grille"):
          infos["grille"] += g.text + ","
        infos["keyCodes"] = infos["grille"].split(",")

        url = base_url + '/cvcsgenimage?modeClavier=0&cryptogramme=' + infos["cryptogramme"]
        img = Captcha(self.browser.openurl(url), infos)

        try:
            img.build_tiles()
        except TileError, err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        self.browser.openurl(url_login)
        self.browser.select_form('authentification')
        self.browser.set_all_readonly(False)

        self.browser['codcli'] = login
        self.browser['codsec'] = img.get_codes(password)
        self.browser['cryptocvcs'] = infos["cryptogramme"]
        self.browser.submit()

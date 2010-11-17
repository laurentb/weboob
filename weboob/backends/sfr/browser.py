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


import urllib

from .pages.login import LoginPage

from weboob.tools.browser import BaseBrowser


__all__ = ['SfrBrowser']


class SfrBrowser(BaseBrowser):
    DOMAIN = 'www.sfr.fr'
    PAGES = {
        'https://www.sfr.fr/cas/login\?service=.*': LoginPage,
        }

    is_logging = False

    def home(self):
        pass

    def is_logged(self):
        return not self.is_on_page(LoginPage) or self.is_logging

    def login(self):
        self.is_logging = True
        service_url = 'http://www.sfr.fr/xmscomposer/j_spring_cas_security_check'
        self.location('https://www.sfr.fr/cas/login?service=%s' % urllib.quote_plus(service_url))
        self.page.login(self.username, self.password)
        self.is_logging = False

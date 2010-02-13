# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.tools.browser import Browser
from weboob.backends.dlfp.pages.index import IndexPage, LoginPage

class DLFP(Browser):
    DOMAIN = 'linuxfr.org'
    PROTOCOL = 'https'
    PAGES = {'https://linuxfr.org/': IndexPage,
             'https://linuxfr.org/pub/': IndexPage,
             'https://linuxfr.org/my/': IndexPage,
             'https://linuxfr.org/login.html': LoginPage,
            }

    def home(self):
        return self.location('https://linuxfr.org')

    def login(self):
        self.location('/login.html', 'login=%s&passwd=%s&isauto=1' % (self.username, self.password))

    def isLogged(self):
        return (self.page and self.page.isLogged())

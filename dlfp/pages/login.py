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

from dlfp.pages.base import BasePage

class IndexPage(BasePage):
    pass

class LoginPage(BasePage):
    def hasError(self):
        plist = self.document.getElementsByTagName('p')
        for p in plist:
            p = p.childNodes[0]
            if hasattr(p, 'data') and p.data.startswith(u'Vous avez rentrÃ© un mauvais mot de passe'):
                return True
        return False

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

from weboob.tools.browser import BrowserIncorrectPassword, BasePage

class DLFPPage(BasePage):
    def is_logged(self):
        for form in self.document.getiterator('form'):
            if form.attrib.get('id', None) == 'formulaire':
                return False

        return True

class IndexPage(DLFPPage):
    pass

class LoginPage(DLFPPage):
    def loaded(self):
        if self.has_error():
            raise BrowserIncorrectPassword()

    def has_error(self):
        for p in self.document.getiterator('p'):
            if p.text and p.text.startswith(u'Vous avez rentré un mauvais mot de passe'):
                return True
        return False

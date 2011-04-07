# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


from weboob.tools.browser import BrowserIncorrectPassword, BasePage

class DLFPPage(BasePage):
    def is_logged(self):
        for form in self.document.getiterator('form'):
            if form.attrib.get('id', None) == 'new_account_sidebar':
                return False

        return True

class IndexPage(DLFPPage):
    pass

class LoginPage(DLFPPage):
    def on_loaded(self):
        if self.has_error():
            raise BrowserIncorrectPassword()

    def has_error(self):
        for p in self.document.getiterator('p'):
            if p.text and p.text.startswith(u'Vous avez rentré un mauvais mot de passe'):
                return True
        return False

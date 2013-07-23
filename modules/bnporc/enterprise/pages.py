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

from weboob.tools.browser import BasePage

__all__ = ['LoginPage', 'AccountsPage']


class BEPage(BasePage):
    def get_error(self):
        for title in self.document.xpath('/html/head/title'):
            if 'erreur' in title.text or 'error' in title.text:
                return self.parser.select(self.document.getroot(),
                                          'input[@name="titre_page"]', 1).value


class LoginPage(BEPage):
    def login(self, username, password):
        raise NotImplementedError()


class AccountsPage(BEPage):
    pass

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.deprecated.browser import BrowserUnavailable, Page as _BasePage


class BasePage(_BasePage):
    def on_loaded(self):
        errors = []
        for div in self.parser.select(self.document.getroot(), 'div.poetry'):
            errors.append(self.parser.tocleanstring(div))

        if len(errors) > 0:
            raise BrowserUnavailable(', '.join(errors))

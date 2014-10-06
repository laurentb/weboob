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


from weboob.deprecated.browser import Page


class PhpBBPage(Page):
    def is_logged(self):
        return len(self.document.getroot().cssselect('li.icon-register')) == 0

    def get_feed_url(self):
        links = self.document.getroot().cssselect('link[type="application/atom+xml"]')
        return links[-1].attrib['href']

    def get_error_message(self):
        errors = []
        for div in self.parser.select(self.document.getroot(), 'div.error,p.error'):
            if div.text:
                errors.append(div.text.strip())
        return ', '.join(errors)


class LoginPage(PhpBBPage):
    pass

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser.pages import HTMLPage


class PhpBBPage(HTMLPage):
    @property
    def logged(self):
        return len(self.doc.xpath('//li[has-class("icon-register")]')) == 0

    def get_feed_url(self):
        links = self.doc.xpath('//link[@type="application/atom+xml"]')
        return links[-1].attrib['href']

    def get_error_message(self):
        errors = []
        for div in self.doc.xpath('//div[has-class("error")] | //p[has-class("error")]'):
            if div.text:
                errors.append(div.text.strip())
        return ', '.join(errors)


class LoginPage(PhpBBPage):
    pass

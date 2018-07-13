# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Florent Fourcot
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

from __future__ import unicode_literals

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.capabilities.profile import Profile
from weboob.browser.filters.standard import CleanText, Regexp


class ProfilePage(LoggedPage, HTMLPage):
    def get_profile(self):
        p = Profile()
        p.name = CleanText('//div[address]/div')(self.doc)
        p.address = CleanText('//div/address')(self.doc)
        p.email = CleanText('//div[contains(text(), "Mon email")]/span')(self.doc)

        for phone in self.doc.xpath('//div[@id="containerRIO"]//option[not(@value="")]'):
            if p.name == Regexp(CleanText('.'), r'(.*) - \d{10}')(phone):
                p.phone = Regexp(CleanText('.'), r'(\d{10})')(phone)
                break

        return p

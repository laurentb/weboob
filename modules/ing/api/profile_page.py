# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, Format
from weboob.browser.elements import ItemElement, method
from weboob.capabilities.profile import Profile
from weboob.capabilities.base import NotAvailable


class ProfilePage(LoggedPage, JsonPage):
    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = Format('%s %s', Dict('name/firstName'), Dict('name/lastName'))
        obj_country = Dict('mailingAddress/country')
        obj_phone = Dict('phones/0/number', default=NotAvailable)
        obj_email = Dict('emailAddress')

        obj_address = CleanText(Format(
            '%s %s %s %s %s %s %s',
            Dict('mailingAddress/address1'),
            Dict('mailingAddress/address2'),
            Dict('mailingAddress/address3'),
            Dict('mailingAddress/address4'),
            Dict('mailingAddress/city'),
            Dict('mailingAddress/postCode'),
            Dict('mailingAddress/country')
        ))

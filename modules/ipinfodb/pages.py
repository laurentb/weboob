# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
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


from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, method
from weboob.capabilities.geolocip import IpLocation
from weboob.browser.filters.standard import Regexp, CleanText, Type
from weboob.capabilities.base import NotAvailable


class HomePage(HTMLPage):
    def search(self, ipaddr):
        form = self.get_form(xpath='//form[contains(@id, "search_form")]')
        form['ip'] = ipaddr
        form.submit()


class LocationPage(HTMLPage):
    @method
    class get_location(ItemElement):
        klass = IpLocation

        obj_id = CleanText('//ul/li[starts-with(.,"IP address :")]/strong')

        obj_city = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"City :")]/text()'),
            'City : (.*)'), default=NotAvailable)

        obj_country = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"Country :")]/text()'),
            'Country : (.*)'), default=NotAvailable)

        obj_region = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"State/Province :")]/text()'),
            'State/Province : (.*)'), default=NotAvailable)

        obj_lt = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"Latitude :")]/text()'),
            'Latitude : (.*)'), default=NotAvailable) & Type(type=float)

        obj_lg = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"Longitude :")]/text()'),
            'Longitude : (.*)'), default=NotAvailable) & Type(type=float)

        obj_zipcode = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"Zip or postal code :")]/text()'),
            'Zip or postal code : (.*)'), default=NotAvailable)

        obj_host = CleanText(Regexp(CleanText('//ul/li[starts-with(.,"Hostname :")]/text()'),
            'Hostname : (.*)'), default=NotAvailable)


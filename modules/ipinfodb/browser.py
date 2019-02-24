# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
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


from weboob.browser import PagesBrowser
from weboob.browser.url import URL
from weboob.browser.profiles import Firefox

from .pages import LocationPage


__all__ = ['IpinfodbBrowser']


class IpinfodbBrowser(PagesBrowser):
    PROFILE = Firefox()
    TIMEOUT = 30

    BASEURL = 'https://ipinfodb.com/'
    home = URL('$', LocationPage)

    def get_location(self, ipaddr):
        self.home.go(data={'ip': ipaddr})
        return self.page.get_location()


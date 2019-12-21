# -*- coding: utf-8 -*-

# Copyright(C) 2019      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.browser import PagesBrowser, URL

from .pages import AllPage


class AirparifBrowser(PagesBrowser):
    BASEURL = 'https://airparif.asso.fr'

    all_page = URL(r'/stations/indicepolluant/', AllPage)

    def iter_gauges(self):
        self.all_page.go(method='POST', headers={
            # don't remove the following headers, site returns 404 else...
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://airparif.asso.fr/stations/index/',
        })
        return self.page.iter_gauges()

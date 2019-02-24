# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Florent Fourcot
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


from weboob.browser import PagesBrowser, URL
from .pages import ListPage, HistoryPage


__all__ = ['SachsenBrowser']


class SachsenBrowser(PagesBrowser):
    BASEURL = 'http://www.umwelt.sachsen.de'

    homepage = URL('/umwelt/infosysteme/hwims/portal/web/wasserstand-uebersicht.*', ListPage)
    history = URL('/umwelt/infosysteme/hwims/portal/web/wasserstand-pegel-(?P<idgauge>.*)', HistoryPage)

    def get_rivers_list(self):
        return self.homepage.stay_or_go().get_rivers_list()

    def iter_history(self, sensor, **kwargs):
        self.history.go(idgauge=sensor.gaugeid)
        return self.page.iter_history(sensor=sensor)

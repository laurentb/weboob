# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Florent Fourcot
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


from weboob.browser import PagesBrowser, URL
from .pages import ListPage, HistoryPage


__all__ = ['SachsenBrowser']


class SachsenBrowser(PagesBrowser):
    BASEURL = 'http://www.umwelt.sachsen.de'

    homepage = URL('/de/wu/umwelt/lfug/lfug-internet/hwz/inhalt_re.html.*', ListPage)
    history = URL('/de/wu/umwelt/lfug/lfug-internet/hwz/MP/(?P<idgauge>.*)/index.html', HistoryPage)

    def get_rivers_list(self):
        return self.homepage.stay_or_go().get_rivers_list()

    def iter_history(self, sensor, **kwargs):
        self.history.go(idgauge=sensor.gaugeid)
        return self.page.iter_history(sensor=sensor)

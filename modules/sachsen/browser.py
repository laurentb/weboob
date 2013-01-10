# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Florent Fourcot
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


from weboob.tools.browser import BaseBrowser


from .pages import ListPage, HistoryPage


__all__ = ['SachsenBrowser']


class SachsenBrowser(BaseBrowser):
    DOMAIN = u'www.umwelt.sachsen.de'
    ENCODING = None
    PAGES = {'.*inhalt_re.html.*': ListPage,
             '.*hwz/MP/.*': HistoryPage
            }

    homepage = '/de/wu/umwelt/lfug/lfug-internet/hwz/inhalt_re.html'

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location(self.homepage)

    def get_rivers_list(self):
        if not self.is_on_page(ListPage):
            self.location(self.homepage)
        return self.page.get_rivers_list()

    def iter_history(self, sensor):
        self.location('/de/wu/umwelt/lfug/lfug-internet/hwz/MP/%d/index.html'
                % int(sensor.gaugeid))
        return self.page.iter_history(sensor)

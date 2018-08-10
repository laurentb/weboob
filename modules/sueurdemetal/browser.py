# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

from weboob.browser import URL, PagesBrowser
from weboob.tools.json import json

from .pages import ConcertListPage, ConcertPage, NoEvent

__all__ = ['SueurDeMetalBrowser']


class SueurDeMetalBrowser(PagesBrowser):
    BASEURL = 'http://www.sueurdemetal.com'

    concerts = URL(r'/func/listconcert-timeline.php', ConcertListPage)
    concert = URL(r'/func/funcGetEvent.php', ConcertPage)

    def __init__(self, *args, **kwargs):
        super(SueurDeMetalBrowser, self).__init__(*args, **kwargs)
        self.cities = {}

    def jlocation(self, *args, **kwargs):
        kwargs.setdefault('headers', {})['Content-Type'] = 'application/json;charset=utf-8'
        kwargs['data'] = json.dumps(kwargs['data'])
        return super(SueurDeMetalBrowser, self).location(*args, **kwargs)

    def search_city(self, city):
        self.jlocation(self.concerts.build(), data={
            'date': '00',
            'dep': '00',
            'salle': '00',
            'groupes': '00',
            'ville': city,
        })
        return self.page.iter_concerts()

    def get_concert(self, id):
        self.jlocation(self.concert.build(), data={
            'id': id,
        })
        try:
            return self.page.get_concert()
        except NoEvent:
            return None

    def build_cities(self):
        if self.cities:
            return
        self.deps.go()
        for dept in self.page.get_depts():
            self.jlocation(self.cities.build, data={
                'annee': '00',
                '': '',
            })

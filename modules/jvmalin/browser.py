# -*- coding: utf-8 -*-

# Copyright(C) 2013 Alexandre Lissy
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


from weboob.deprecated.browser import Browser
from .pages import RoadmapSearchPage, RoadmapResultsPage, RoadmapPage, RoadmapAmbiguity


__all__ = ['JVMalin']


class JVMalin(Browser):
    DOMAIN = 'www.jvmalin.fr'
    PAGES = {
        'http://www\.jvmalin\.fr/Itineraires/Recherche.*': RoadmapSearchPage,
        'http://www\.jvmalin\.fr/Itineraires/Precision.*': RoadmapResultsPage,
        'http://www\.jvmalin\.fr/route/vuesearch/result.*': RoadmapPage
    }

    def __init__(self, **kwargs):
        Browser.__init__(self, '', **kwargs)

    def get_roadmap(self, departure, arrival, filters):
        self.location('/Itineraires/Recherche')

        assert self.is_on_page(RoadmapSearchPage)
        self.page.search(departure, arrival, filters.departure_time, filters.arrival_time)

        assert self.is_on_page(RoadmapResultsPage)

        dest = ''
        try:
            dest = self.page.find_best()
        except RoadmapAmbiguity:
            self.page.resubmit_best_form()
            assert self.is_on_page(RoadmapResultsPage)
            dest = self.page.find_best()

        self.location(dest)

        roadmap = {}
        roadmap['steps'] = list(self.page.get_steps())
        return roadmap

    def is_logged(self):
        """ Do not need to be logged """
        return True

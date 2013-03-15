# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Hébert, Romain Bignon
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


from weboob.tools.browser import BaseBrowser, BasePage, BrowserUnavailable

from .pages.departures import DeparturesPage
from .pages.roadmap import RoadmapSearchPage, RoadmapConfirmPage, RoadmapPage


class UnavailablePage(BasePage):
    def on_loaded(self):
        raise BrowserUnavailable('Website is currently unavailable')


class Transilien(BaseBrowser):
    DOMAIN = 'www.transilien.com'
    PROTOCOL = 'https'
    USER_AGENT = BaseBrowser.USER_AGENTS['microb']
    PAGES = {'https://www\.transilien\.com/web/ITProchainsTrainsAvecDest\.do\?.*': DeparturesPage,
             'https://www\.transilien\.com/web/ITProchainsTrains\.do\?.*':         DeparturesPage,
             'https://www\.transilien\.com/web/site.*':                            RoadmapSearchPage,
             'https://www\.transilien\.com/web/RedirectHI.do.*':                   RoadmapConfirmPage,
             'https://www\.transilien\.com/web/RedirectHIIntermediaire.do.*':      RoadmapPage,
             'https://www\.transilien\.com/transilien_sncf_maintenance_en_cours.htm': UnavailablePage,
            }

    def is_logged(self):
        """ Do not need to be logged """
        return True

    def iter_station_search(self, pattern):
        pass

    def iter_station_departures(self, station_id, arrival_id=None):
        if arrival_id:
            self.location('https://www.transilien.com/web/ITProchainsTrainsAvecDest.do?codeTr3aDepart=%s&codeTr3aDest=%s&urlModule=/site/pid/184&gareAcc=true' % (station_id, arrival_id))
        else:
            self.location('https://www.transilien.com/web/ITProchainsTrains.do?tr3a=%s&urlModule=/site/pid/184' % station_id)

        return self.page.iter_routes()

    def get_roadmap(self, departure, arrival, filters):
        self.location('/web/site/accueil/etat-trafic/chercher-itineraire/lang/en')

        assert self.is_on_page(RoadmapSearchPage)
        self.page.search(departure, arrival, filters.departure_time, filters.arrival_time)

        assert self.is_on_page(RoadmapConfirmPage)
        self.page.confirm()

        assert self.is_on_page(RoadmapPage)
        roadmap = {}
        roadmap['steps'] = list(self.page.get_steps())
        return roadmap

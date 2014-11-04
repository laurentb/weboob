# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Hébert, Romain Bignon
# Copyright(C) 2014 Benjamin Carton
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
from datetime import datetime

from weboob.browser import PagesBrowser, URL
from .pages import StationsPage, DeparturesPage, DeparturesPage2, HorairesPage, RoadMapPage


class Transilien(PagesBrowser):

    BASEURL = 'http://www.transilien.com'
    stations_page = URL('aidesaisie/autocompletion\?saisie=(?P<pattern>.*)', StationsPage)
    departures_page = URL('gare/pagegare/chargerGare\?nomGare=(?P<station>.*)',
                          'gare/.*', DeparturesPage)
    departures_page2 = URL('fichehoraire/fichehoraire/(?P<url>.*)',
                           'fichehoraire/fichehoraire/.*', DeparturesPage2)

    horaires_page = URL('fiche-horaire/(?P<station>.*)--(?P<arrival>.*)-(?P<station2>.*)-(?P<arrival2>)-(?P<date>)',
                        'fiche-horaire/.*', HorairesPage)

    roadmap_page = URL('itineraire/rechercheitineraire/(?P<url>.*)',
                       'itineraire/rechercheitineraire/.*', RoadMapPage)

    def get_roadmap(self, departure, arrival, filters):
        dep = self.get_stations(departure, False).next().name
        arr = self.get_stations(arrival, False).next().name
        self.roadmap_page.go(url='init').request_roadmap(dep, arr, filters.arrival_time)
        if self.page.is_ambiguous():
            self.page.fix_ambiguity()
        return self.page.get_roadmap()

    def get_stations(self, pattern, only_station=True):
        return self.stations_page.go(pattern=pattern).get_stations(only_station=only_station)

    def get_station_departues(self, station, arrival_id, date):
        if arrival_id is not None:
            arrival_name = arrival_id.replace('-', ' ')
            self.departures_page2.go(url='init').init_departure(station)

            arrival = self.page.get_potential_arrivals().get(arrival_name)
            if arrival:
                station_id = self.page.get_station_id()

                if date is None:
                    date = datetime.now()

                _date = datetime.strftime(date, "%d/%m/%Y-%H:%M")

                self.horaires_page.go(station=station.replace(' ', '-'), arrival=arrival_id, station2=station_id,
                                      arrival2=arrival, date=_date)
                return self.page.get_departures(station, arrival_name, date)
            return []
        else:
            return self.departures_page.go(station=station).get_departures(station=station)

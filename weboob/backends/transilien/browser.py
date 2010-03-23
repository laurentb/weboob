# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Julien Hébert, Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from datetime import datetime, date, time
import HTMLParser

from weboob.tools.browser import Browser
from weboob.tools.misc import toUnicode

from .pages.route import RoutePage

class Route(object):
    "une ligne code_mission | time"
    def __init__(self, code_mission, time, destination, platform):
        self.code_mission = code_mission
        self.time = time
        self.destination = destination
        self.platform = platform

    def __repr__(self):
        return "<Route %s %s %s %s>" % (self.code_mission,
            self.time, self.destination, self.platform)

class Parser(HTMLParser.HTMLParser):
    "Parse les tableaux html contenant les horaires"
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.__table_horaires3 = False
        self.__code_de_mission = False
        self.__a_code_de_mission = False
        self.__time = False
        self.__destination = False
        self.__platform = False
        self.__liste_train = []
        self.__liste_horaire = []
        self.__liste_destination = []
        self.__liste_platform = []

    def parse(self, data):
        self.feed(data.read())
        return self

    def handle_starttag(self, tag, attrs):
        "execute a chaque balise ouvrante"
        if (tag == 'table' and (dict(attrs)['class'] == 'horaires3')):
            self.__table_horaires3 = True

        elif self.__table_horaires3 and tag == 'td':
            try:
                self.__code_de_mission = (
                    dict(attrs)['headers'] == 'Code_de_mission')
                self.__time = (
                    dict(attrs)['headers'] == 'Heure_de_passage')
                self.__destination = (
                    dict(attrs)['headers'] == 'Destination')
                self.__platform = (
                    dict(attrs)['headers'] == 'Voie')
            except KeyError:
                if dict(attrs).has_key('headers'):
                    raise
                else:
                    pass
        else:
            self.__a_code_de_mission = (tag == 'a' and self.__code_de_mission)

    def handle_data(self, data):
        "execute pour chaque contenu de balise"
        if self.__a_code_de_mission:
            self.__liste_train.append(data.strip())
        if self.__time and data.strip() != '*':
            self.__liste_horaire.append(data.strip())
        if self.__destination:
            self.__liste_destination.append(data.strip())
        if self.__platform:
            self.__liste_platform.append(data.strip())

    def handle_endtag(self, tag):
        "execute à chaque balise fermante"
        self.__a_code_de_mission ^= (self.__a_code_de_mission and tag == 'a')
        self.__time ^= (self.__time and tag == 'td')
        self.__destination ^= (self.__destination and tag == 'td')
        self.__platform ^= (self.__platform and tag == 'td')


    @property
    def list_route(self):
        "getter"
        __list_route = []
        __curseur_horaire = 0
        for __i in self.__liste_train:
            __list_route.append(Route(
                code_mission=__i,
                time=self.__liste_horaire[__curseur_horaire],
                destination=self.__liste_destination[__curseur_horaire],
                platform=self.__liste_platform[__curseur_horaire]
                ))
            __curseur_horaire += 1
        return __list_route

class Transilien(Browser):
    DOMAIN = 'www.transilien.com'
    PROTOCOL = 'http'
    PAGES = {'http://www\.transilien\.com/web/ITProchainsTrainsAvecDest\.do\?.*': RoutePage,
             'http://www\.transilien\.com/web/ITProchainsTrains\.do\?.*': RoutePage
            }

    def __init__(self):
        Browser.__init__(self, '', parser=Parser)

    def iter_station_search(self, pattern):
        pass

    def iter_station_departures(self, station_id, arrival_id=None):
        if arrival_id:
            self.location('http://www.transilien.com/web/ITProchainsTrainsAvecDest.do?codeTr3aDepart=%s&codeTr3aDest=%s&urlModule=/site/pid/184&gareAcc=true' % (station_id, arrival_id))
        else:
            self.location('http://www.transilien.com/web/ITProchainsTrains.do?tr3a=%s&urlModule=/site/pid/184' % station_id)
        for route in self.page.document.list_route:
            yield {'type':        toUnicode(route.code_mission),
                   'time':        datetime.combine(date.today(), time(*[int(x) for x in route.time.split(':')])),
                   'departure':   toUnicode(station_id),
                   'arrival':     toUnicode(route.destination),
                   'late':        time(),
                   'late_reason': toUnicode(route.platform)}

    def home(self):
        pass

    def login(self):
        pass

    def is_logged(self):
        """ Do not need to be logged """
        return True

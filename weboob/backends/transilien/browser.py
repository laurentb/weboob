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


from weboob.tools.browser import BaseBrowser

from .pages.route import RoutePage

class Transilien(BaseBrowser):
    DOMAIN = 'www.transilien.com'
    PROTOCOL = 'https'
    USER_AGENT = BaseBrowser.USER_AGENTS['microb']
    PAGES = {'https://www\.transilien\.com/web/ITProchainsTrainsAvecDest\.do\?.*': RoutePage,
             'https://www\.transilien\.com/web/ITProchainsTrains\.do\?.*':         RoutePage,
            }

    def iter_station_search(self, pattern):
        pass

    def iter_station_departures(self, station_id, arrival_id=None):
        if arrival_id:
            self.location('https://www.transilien.com/web/ITProchainsTrainsAvecDest.do?codeTr3aDepart=%s&codeTr3aDest=%s&urlModule=/site/pid/184&gareAcc=true' % (station_id, arrival_id))
        else:
            self.location('https://www.transilien.com/web/ITProchainsTrains.do?tr3a=%s&urlModule=/site/pid/184' % station_id)

        return self.page.iter_routes()

    def is_logged(self):
        """ Do not need to be logged """
        return True

# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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

from random import randint

from weboob.deprecated.browser import Browser

from .pages import CitiesPage, SearchPage, SearchErrorPage, \
                   SearchInProgressPage, ResultsPage, ForeignPage


__all__ = ['VoyagesSNCFBrowser']


class VoyagesSNCFBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.voyages-sncf.com'
    ENCODING = 'utf-8'

    PAGES = {
        'http://www.voyages-sncf.com/completion/VSC/FR/fr/cityList.js':     (CitiesPage, 'raw'),
        'http://www.voyages-sncf.com/billet-train':                         SearchPage,
        'http://www.voyages-sncf.com/billet-train\?.+':                     SearchErrorPage,
        'http://www.voyages-sncf.com/billet-train/recherche-en-cours.*':    SearchInProgressPage,
        'http://www.voyages-sncf.com/billet-train/resultat.*':              ResultsPage,
        'http://(?P<country>\w{2})\.voyages-sncf.com/\w{2}/.*':             ForeignPage,
    }

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)
        self.addheaders += (('X-Forwarded-For', '82.228.147.%s' % randint(1,254)),)


    def get_stations(self):
        self.location('/completion/VSC/FR/fr/cityList.js')
        return self.page.get_stations()

    def iter_departures(self, departure, arrival, date, age, card, comfort_class):
        self.location('/billet-train')
        self.page.search(departure, arrival, date, age, card, comfort_class)

        return self.page.iter_results()

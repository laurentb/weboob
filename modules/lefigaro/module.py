# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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
"backend for http://www.lefigaro.fr"

from weboob.tools.newsfeed import Newsfeed
from weboob.tools.backend import AbstractModule
from weboob.tools.backend import BackendConfig
from weboob.tools.value import Value

from weboob.capabilities.messages import CapMessages, Thread

from .browser import NewspaperFigaroBrowser
from .tools import rssid


class NewspaperFigaroModule(AbstractModule, CapMessages):
    MAINTAINER = u'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    NAME = 'lefigaro'
    DESCRIPTION = u'Le Figaro French newspaper website'
    BROWSER = NewspaperFigaroBrowser
    RSS_FEED = 'http://rss.lefigaro.fr/lefigaro/laune?format=xml'
    RSSID = staticmethod(rssid)
    RSSSIZE = 30
    PARENT = 'genericnewspaper'
    CONFIG = BackendConfig(Value('feed', label='RSS feed',
                           choices={'actualites': u'actualites',
                                    'flash-actu': u'flash-actu',
                                    'politique': u'politique',
                                    'international': u'international',
                                    'actualite-france': u'actualite-france',
                                    'hightech': u'hightech',
                                    'sciences': u'sciences',
                                    'sante': u'sante',
                                    'lefigaromagazine': u'lefigaromagazine',
                                    'photos': u'photos',
                                    'economie': u'economie',
                                    'societes': u'societes',
                                    'medias': u'medias',
                                    'immobilier': u'immobilier',
                                    'assurance': u'assurance',
                                    'retraite': u'retraite',
                                    'placement': u'placement',
                                    'impots': u'impots',
                                    'conso': u'conso',
                                    'emploi': u'emploi',
                                    'culture': u'culture',
                                    'cinema': u'cinema',
                                    'musique': u'musique',
                                    'livres': u'livres',
                                    'theatre': u'theatre',
                                    'lifestyle': u'lifestyle',
                                    'automobile': u'automobile',
                                    'gastronomie': u'gastronomie',
                                    'horlogerie': u'horlogerie',
                                    'mode-homme': u'mode-homme',
                                    'sortir-paris': u'sortir-paris',
                                    'vins': u'vins',
                                    'voyages': u'voyages',
                                    'sport': u'sport',
                                    'football': u'football',
                                    'rugby': u'rugby',
                                    'tennis': u'tennis',
                                    'cyclisme': u'cyclisme',
                                    'sport-business': u'sport-business'}))

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.RSS_FEED = "http://www.lefigaro.fr/rss/figaro_%s.xml" % self.config['feed'].get()

    def iter_threads(self):
        for article in Newsfeed(self.RSS_FEED, self.RSSID).iter_entries():
            thread = Thread(article.id)
            thread.title = article.title
            thread.date = article.datetime
            yield(thread)

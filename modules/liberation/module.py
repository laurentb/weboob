# -*- coding: utf-8 -*-

# Copyright(C) 2013 Florent Fourcot
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
"backend for http://liberation.fr"

from weboob.tools.newsfeed import Newsfeed
from weboob.capabilities.messages import CapMessages, Thread
from weboob.tools.backend import AbstractModule
from weboob.tools.backend import BackendConfig
from weboob.tools.value import Value
from .browser import NewspaperLibeBrowser
from .tools import rssid, url2id


class NewspaperLibeModule(AbstractModule, CapMessages):
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    NAME = 'liberation'
    DESCRIPTION = u'Libération newspaper website'
    BROWSER = NewspaperLibeBrowser
    RSSID = staticmethod(rssid)
    URL2ID = staticmethod(url2id)
    RSSSIZE = 30
    PARENT = 'genericnewspaper'
    CONFIG = BackendConfig(Value('feed', label='RSS feed',
                           choices={'9': u'A la une sur Libération',
                                    '10': u'Monde',
                                    '11': u'Politiques',
                                    '12': u'Société',
                                    '13': u'Économie',
                                    '14': u'Sports',
                                    '17': u'Labo: audio, vidéo, diapos, podcasts',
                                    '18': u'Rebonds',
                                    '44': u'Les chroniques de Libération',
                                    '53': u'Écrans',
                                    '54': u'Next',
                                    '58': u'Cinéma'
                                    }))

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.RSS_FEED = "http://www.liberation.fr/rss/%s" % self.config['feed'].get()

    def iter_threads(self):
        for article in Newsfeed(self.RSS_FEED, self.RSSID).iter_entries():
            thread = Thread(article.id)
            thread.title = article.title
            thread.date = article.datetime
            yield(thread)

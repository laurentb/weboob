# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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
"backend for http://www.ecrans.fr"

import time 

from weboob.capabilities.messages import ICapMessages, Thread
from weboob.tools.capabilities.messages.GenericBackend import GenericNewspaperBackend
from .browser import NewspaperEcransBrowser
from .tools import rssid, url2id
from weboob.tools.newsfeed import Newsfeed

class NewspaperEcransBackend(GenericNewspaperBackend, ICapMessages):
    MAINTAINER = 'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.b'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    NAME = 'ecrans'
    DESCRIPTION = u'Écrans French news website'
    BROWSER = NewspaperEcransBrowser
    RSS_FEED = 'http://www.ecrans.fr/spip.php?page=backend'
    RSSID = rssid

    def set_message_read(self, message):
        self.storage.set(
            'seen',
            message.thread.id,
            'comments',
            self.storage.get(
                'seen',
                message.thread.id,
                'comments',
                default=[]) + [message.id])

        lastpurge = self.storage.get('lastpurge', default=0)
        l = []
        if time.time() - lastpurge > 7200:
            self.storage.set('lastpurge', time.time())
            # Get lasts 20 articles
            for id in self.storage.get('seen', default={}): 
                 l.append((int(url2id(id)), id))
            l.sort()
            l.reverse()
            tosave = [v[1] for v in l[0:19]]
            toremove = set([v for v in self.storage.get('seen', default={})]).difference(tosave)
            for id in toremove: 
                self.storage.delete('seen', id)
                
        self.storage.save()


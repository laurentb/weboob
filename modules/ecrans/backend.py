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

from weboob.capabilities.messages import ICapMessages
from weboob.tools.capabilities.messages.GenericBackend import GenericNewspaperBackend
from .browser import NewspaperEcransBrowser
from .tools import rssid, url2id


class NewspaperEcransBackend(GenericNewspaperBackend, ICapMessages):
    MAINTAINER = u'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.e'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    NAME = 'ecrans'
    DESCRIPTION = u'Écrans French news website'
    BROWSER = NewspaperEcransBrowser
    RSS_FEED = 'http://www.ecrans.fr/spip.php?page=backend'
    RSSID = staticmethod(rssid)
    URL2ID = staticmethod(url2id)
    # RSS Size is actually 10, but some articles are not sorted by publication date
    RSSSIZE = 40

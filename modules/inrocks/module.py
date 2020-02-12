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
"backend for http://www.lesinrocks.com"

from weboob.tools.backend import AbstractModule
from weboob.capabilities.messages import CapMessages

from .browser import NewspaperInrocksBrowser
from .tools import rssid


class NewspaperInrocksModule(AbstractModule, CapMessages):
    MAINTAINER = u'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '2.0'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    NAME = 'inrocks'
    DESCRIPTION = u'Les Inrocks French news website'
    BROWSER = NewspaperInrocksBrowser
    RSS_FEED = 'http://www.lesinrocks.com/fileadmin/rss/actus.xml'
    RSSID = rssid
    PARENT = 'genericnewspaper'

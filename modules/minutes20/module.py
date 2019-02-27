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
"backend for http://20minutes.fr"

from weboob.capabilities.messages import CapMessages
from weboob.tools.backend import AbstractModule
from .browser import Newspaper20minutesBrowser
from .tools import rssid


class Newspaper20minutesModule(AbstractModule, CapMessages):
    MAINTAINER = u'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '1.6'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    NAME = 'minutes20'
    DESCRIPTION = u'20 Minutes French newspaper website'
    BROWSER = Newspaper20minutesBrowser
    RSS_FEED = 'http://www.20minutes.fr/rss/une.xml'
    RSSID = rssid
    PARENT = 'genericnewspaper'

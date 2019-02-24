# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent Ardisson
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

from __future__ import unicode_literals


from weboob.tools.backend import Module
from weboob.capabilities.bank import CapBank

from .browser import LinebourseBrowser


__all__ = ['LinebourseModule']


class LinebourseModule(Module, CapBank):
    NAME = 'linebourse'
    DESCRIPTION = u'linebourse website'
    MAINTAINER = u'Vincent Ardisson'
    EMAIL = 'vardisson@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = LinebourseBrowser

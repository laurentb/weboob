# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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


from weboob.tools.backend import AbstractModule
from weboob.capabilities.bank import CapBank
from weboob.capabilities.contact import CapContact


__all__ = ['CmbModule']


class CmbModule(AbstractModule, CapBank, CapContact):
    NAME = 'cmb'
    MAINTAINER = u'Edouard Lambert'
    EMAIL = 'elambert@budget-insight.com'
    VERSION = '1.3'
    DESCRIPTION = u'Credit Mutuel de Bretagne'
    LICENSE = 'AGPLv3+'
    PARENT = 'cmso'

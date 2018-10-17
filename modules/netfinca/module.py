# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget-Insight
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.tools.backend import Module

from .browser import NetfincaBrowser

__all__ = ['NetfincaModule']


class NetfincaModule(Module):
    NAME = 'netfinca'
    DESCRIPTION = 'netfinca website'
    MAINTAINER = 'Martin Sicot'
    EMAIL = 'martin.sicot@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.4'

    BROWSER = NetfincaBrowser

# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


import re

from weboob.browser import AbstractBrowser


class GanAssurances(AbstractBrowser):
    PARENT = 'groupama'
    PARENT_ATTR = 'package.browser.GroupamaBrowser'

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'https://%s' % website
        self.website = re.findall('espaceclient.(.*?).fr', self.BASEURL)[0]
        super(GanAssurances, self).__init__(*args, **kwargs)

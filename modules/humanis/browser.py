# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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


from weboob.browser import AbstractBrowser, URL

from .pages import LoginPage

class HumanisBrowser(AbstractBrowser):
    PARENT = 'cmes'

    login = URL('(?P<subsite>.*)fr/identification/login.cgi', LoginPage)

    def __init__(self, weboob, baseurl, subsite, login, password, *args, **kwargs):
        self.weboob = weboob

        super(self.__class__, self).__init__(baseurl, login, password, subsite, *args, **kwargs)

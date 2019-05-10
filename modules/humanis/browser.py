# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import AbstractBrowser, URL

from .pages import LoginPage

class HumanisBrowser(AbstractBrowser):
    PARENT = 'cmes'

    login = URL('epsens/(?P<client_space>.*)fr/identification/authentification.html', LoginPage)

    client_space = ''

    def __init__(self, login, password, baseurl, subsite, *args, **kwargs):
        self.weboob = kwargs['weboob']
        super(HumanisBrowser, self).__init__(login, password, baseurl, subsite, *args, **kwargs)

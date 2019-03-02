# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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

from .pages import LoginPage
from weboob.browser.browsers import AbstractBrowser
from weboob.browser.profiles import Wget
from weboob.browser.url import URL

__all__ = ['CICBrowser']


class CICBrowser(AbstractBrowser):
    PROFILE = Wget()
    TIMEOUT = 30
    BASEURL = 'https://www.cic.fr'
    PARENT = 'creditmutuel'

    login =       URL('/fr/authentification.html',
                      '/sb/fr/banques/particuliers/index.html',
                      '/(?P<subbank>.*)/fr/$',
                      '/(?P<subbank>.*)/fr/banques/accueil.html',
                      '/(?P<subbank>.*)/fr/banques/particuliers/index.html',
                      LoginPage)

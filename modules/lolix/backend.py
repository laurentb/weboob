# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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

from weboob.tools.backend import BaseBackend  #, BackendConfig
#  from weboob.tools.value import Value

from .browser import LolixBrowser

from weboob.capabilities.job import ICapJob


__all__ = ['LolixBackend']


class LolixBackend(BaseBackend, ICapJob):
    NAME = 'lolix'
    DESCRIPTION = u'Lolix est un centre de compétences spécialisé dans les technologies à base de Logiciel Libre.'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.g'

    BROWSER = LolixBrowser

    def search_job(self, pattern=None):
        with self.browser:
            for advert in self.browser.search_job():
                yield advert

    def get_job_advert(self, _id, advert):
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from logging import debug

from weboob.capabilities.video import ICapVideo
from weboob.core.backend import BaseBackend

from .browser import InaBrowser


__all__ = ['InaBackend']


class InaBackend(BaseBackend, ICapVideo):
    NAME = 'ina'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.1'
    DESCRIPTION = 'INA french video archives'
    LICENSE = 'GPLv3'

    BROWSER = InaBrowser

    def get_video(self, _id):
        return self.browser.get_video(_id)

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False):
        debug(u'backend ina: iter_search_results is not implemented')
        return []

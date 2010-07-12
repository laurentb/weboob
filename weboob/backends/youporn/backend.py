# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


from weboob.core.backend import BaseBackend
from weboob.capabilities.video import ICapVideo

from .browser import YoupornBrowser


__all__ = ['YoupornBackend']


class YoupornBackend(BaseBackend, ICapVideo):
    NAME = 'youporn'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.1'
    DESCRIPTION = 'Youporn videos website'
    LICENSE = 'GPLv3'

    BROWSER = YoupornBrowser

    def get_video(self, _id):
        return self.browser.get_video(_id)

    SORTBY = ['relevance', 'rating', 'views', 'time']
    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False):
        if not nsfw:
            return iter(set())
        return self.browser.iter_search_results(pattern, self.SORTBY[sortby])

    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


from weboob.deprecated.browser import Browser
from weboob.deprecated.browser.decorators import id2url

from .pages.video import VideoPage
from .pages.search import SearchPage
from .video import InaVideo


__all__ = ['InaBrowser']


class InaBrowser(Browser):
    DOMAIN = 'ina.fr'
    PAGES = {'http://player.ina.fr/notices/.+\.mrss': (VideoPage, 'xml'),
             'http://boutique\.ina\.fr/recherche/.+': SearchPage,
             }

    @id2url(InaVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video)

    def search_videos(self, pattern):
        self.location(self.buildurl('http://boutique.ina.fr/recherche/recherche', search=pattern.encode('utf-8')))
        assert self.is_on_page(SearchPage)
        return self.page.iter_videos()

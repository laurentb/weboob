# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.file import SearchSort

from .pages import ListPage, APIPage


__all__ = ['VimeoBrowser']


SORT_NAME = {
    SearchSort.RELEVANCE: 'relevance',
    SearchSort.RATING: 'popularity',
    SearchSort.VIEWS: 'popularity',
    SearchSort.DATE: 'latest',
}

NSFW_FLAGS = {
    True: 255,
    False: 191,
}


class VimeoBrowser(PagesBrowser):
    BASEURL = 'https://vimeo.com'

    api_page = URL(r'https://api.vimeo.com/search', APIPage)
    html_search = URL(r'https://vimeo.com/search/page:(?P<page>\d+)/sort:(?P<sort>\w+)', ListPage)

    def search_videos(self, pattern, sortby, nsfw):
        sortby = SORT_NAME[sortby]
        nsfw = NSFW_FLAGS[nsfw]

        self.html_search.go(page=1, sort=sortby, params={'q': pattern})
        jwt = self.page.get_token()

        params = {
            'query': pattern,
            'filter_type': 'clip',
            'per_page': 18,
            'page': 1,
            'sort': sortby,
            'fields': 'search_web,mature_hidden_count',
            'container_fields': 'parameters,effects,search_id,stream_id,mature_hidden_count',
            'direction': 'desc',
            'filter_mature': nsfw,
        }
        self.api_page.go(params=params, headers={'Authorization': 'jwt %s' % jwt})
        return self.page.iter_videos()

# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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

from __future__ import unicode_literals

from weboob.browser import PagesBrowser, URL
from weboob.tools.json import json
from .pages import SearchPage, HomePage

import time

__all__ = ['PluzzBrowser']


class PluzzBrowser(PagesBrowser):
    BASEURL = 'https://www.france.tv'
    PROGRAMS = None

    search_page = URL(r'https://vwdlashufe-dsn.algolia.net/1/indexes/\*/queries\?(?P<p>.*)', SearchPage)
    home = URL(r'/(?P<cat>.*)', HomePage)
    base = URL(r'/', HomePage)

    def search_videos(self, s):
        self.go_home()
        algolia_app_id, algolia_api_key = self.page.get_params()

        params = "x-algolia-agent=Algolia for vanilla JavaScript (lite) 3.27.0;instantsearch.js 2.10.2;JS Helper 2.26.0&x-algolia-application-id="+algolia_app_id+"&x-algolia-api-key="+algolia_api_key

        data = {}
        data['requests'] = [0]
        data['requests'][0] = {}
        data['requests'][0]['indexName'] = "yatta_prod_contents"
        ts = int(time.time())
        data['requests'][0]['params'] = 'query={}&hitsPerPage=20&page=0&filters=class:video AND ranges.replay.web.begin_date < {} AND ranges.replay.web.end_date > {}&facetFilters=["class:video"]&facets=[]&tagFilters='.format(s, ts, ts)
        return self.search_page.go(p=params, data=json.dumps(data)).iter_videos()

    def get_categories(self, cat=""):
        for cat in self.home.go(cat=cat).iter_categories():
            yield cat

    def get_subcategories(self, cat):
        for cat in self.home.go(cat=cat).iter_subcategories(cat=cat):
            yield cat

    def get_emissions(self, cat):
        for cat in self.home.go(cat="%s.html" % "/".join(cat)).iter_emissions(cat=cat):
            yield cat

    def iter_videos(self, cat=""):
        return self.home.go(cat=cat).iter_videos()

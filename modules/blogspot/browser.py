# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from collections import OrderedDict
from datetime import date

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.messages import Message

from .pages import DatePage, IndexPage, ArticlePage


class BlogspotBrowser(PagesBrowser):
    BASEURL = 'http://www.blogspot.com'

    index = URL(r'/$', IndexPage)
    date = URL(r'/\?action=getTitles&widgetId=BlogArchive1&widgetType=BlogArchive&responseType=js&path=(?P<query>.*)', r'/(?P<year>\d+)/(?P<month>\d+)/$', DatePage)
    article = URL(r'/(?P<year>\d+)/(?P<month>\d+)/(?P<title>.*).html$', ArticlePage)

    def __init__(self, baseurl, *args, **kwargs):
        super(BlogspotBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = baseurl
        self.cache = OrderedDict()

    def iter_dates(self):
        if not self.cache:
            self.index.go()
            for url in self.page.get_dates():
                m = self.date.match(url)
                key = (m.group('year'), m.group('month'))
                self.cache[key] = None

        for k in self.cache:
            yield self.build_date(k)

    def iter_articles(self, key):
        if self.cache[key] is None:
            query = self.date.build(year=key[0], month=key[1])
            self.date.go(query=query)
            self.cache[key] = list(self.page.get_articles())

        for j in self.cache[key]:
            yield self.build_article(j)

    def build_date(self, k):
        ret = Message(id='%s.%s' % k)
        ret.title = '%s/%s' % k
        ret.content = ''
        ret.date = date(int(k[0]), int(k[1]), 1)
        ret._type = 'date'
        ret._key = k
        return ret

    def build_article(self, j):
        m = self.article.match(j['url'])
        ret = Message(id=m.group('title'))
        ret.title = j['title']
        ret.url = j['url']
        ret.flags = Message.IS_HTML
        ret.date = date(int(m.group('year')), int(m.group('month')), 1)
        ret.children = []
        ret._type = 'article'
        return ret

    def get_article(self, url):
        self.location(url)
        assert self.article.is_here()
        return self.page.get_message()

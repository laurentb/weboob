# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import feedparser
import re

class Article:
    RSS = None

    def __init__(self, _id, url, title, author, datetime):
        self._id = _id
        self.url = url
        self.title = title
        self.author = author
        self.datetime = datetime

class Newspaper(Article):
    RSS = 'https://linuxfr.org/backend/news/rss20.rss'

class Telegram(Article):
    RSS = 'https://linuxfr.org/backend/journaux/rss20.rss'

class ArticlesList:
    RSS = {'newspaper': Newspaper,
           'telegram':  Telegram
          }

    def __init__(self, section=None):
        self.section = section
        self.articles = []

    def fetch(self):
        for section, klass in self.RSS.iteritems():
            if self.section and self.section != section:
                continue

            url = klass.RSS
            feed = feedparser.parse(url)
            for item in feed['items']:
                m = re.match('.*/([0-9]+).html', item['link'])
                if not m:
                    warning('Unable to parse ID from link \'%s\'' % item['link'])
                    continue
                _id = m.group(1)
                article = klass(_id, item['link'], item['title'], item['author'], item['date_parsed'])
                print _id, item['author'], item['title']

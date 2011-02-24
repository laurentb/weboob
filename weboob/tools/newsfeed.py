# -*- coding: utf-8 -*-

# Copyright(C) 2010 Clément Schreiner
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

import datetime
import feedparser


__all__ = ['Entry', 'Newsfeed']


class Entry:
    def __init__(self, entry, rssid_func=None):
        self.id = entry.id

        if entry.has_key("link"):
            self.link = entry["link"]
        else:
            self.link = None

        if entry.has_key("title"):
            self.title = entry["title"]
        else:
            self.title = None

        if entry.has_key("author"):
            self.author = entry["author"]
        else:
            self.author = None

        if entry.has_key("updated_parsed"):
            self.datetime = datetime.datetime(*entry['updated_parsed'][:7])
        else:
            self.datetime = None

        if entry.has_key("summary"):
            self.summary = entry["summary"]
        else:
            self.summary = None

        self.content = []
        if entry.has_key("content"):
            for i in entry["content"]:
                self.content.append(i.value)
        elif self.summary:
            self.content.append(self.summary)
        else:
            self.content = None

        if rssid_func:
            self.id = rssid_func(self)

class Newsfeed:
    def __init__(self, url, rssid_func=None):
        self.feed = feedparser.parse(url)
        self.rssid_func = rssid_func

    def iter_entries(self):
        for entry in self.feed['entries']:
            yield Entry(entry, self.rssid_func)

    def get_entry(self, id):
        for entry in self.feed['entries']:
            if entry.id == id:
                return Entry(entry, self.rssid_func)

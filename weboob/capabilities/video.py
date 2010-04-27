# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon, Christophe Benz

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

from .cap import ICap


__all__ = ['ICapVideoProvider', 'Video']


class Video(object):
    def __init__(self, _id, title=None, url=None, author=None, duration=0, date=None,
                 rating=0.0, rating_max=0.0, preview_url=None, nsfw=False, id2url=None):
        self.id = _id
        self.title = title
        self.url = url
        self.author = author
        self.duration = int(duration)
        self.date = date
        self.rating = float(rating)
        self.rating_max = float(rating_max)
        self.preview_url = preview_url
        self.nsfw = nsfw
        self.id2url = id2url

    @property
    def formatted_duration(self):
        return '%d:%02d:%02d' % (self.duration / 3600, (self.duration % 3600 / 60), self.duration % 60)

    @property
    def page_url(self):
        if self.id2url:
            return self.id2url(self.id)
        else:
            return None

class ICapVideoProvider(ICap):
    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

    (SEARCH_RELEVANCE,
     SEARCH_RATING,
     SEARCH_VIEWS,
     SEARCH_DATE) = range(4)

    def iter_search_results(self, pattern=None, sortby=SEARCH_RELEVANCE, nsfw=False):
        """
        Iter results of a search on a pattern. Note that if pattern is None,
        it get the latest videos.

        @param pattern  [str] pattern to search on
        @param sortby  [enum] sort by...
        @param pattern  [bool] include non-suitable for work videos if True
        """
        raise NotImplementedError()

    def get_video(self, _id):
        """
        Get a Video from an ID.

        @param _id  the video id. It can be a numeric ID, or a page url, or so.
        @return  a Video object
        """
        raise NotImplementedError()

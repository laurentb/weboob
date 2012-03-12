# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Christophe Benz
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


from datetime import datetime, timedelta

from .base import IBaseCap, CapBaseObject, NotAvailable
from weboob.tools.capabilities.thumbnail import Thumbnail


__all__ = ['BaseVideo', 'ICapVideo']

class BaseVideo(CapBaseObject):
    """
    Represents a video.
    This object has to be inherited to specify how to calculate the URL of the video from its ID.
    """

    def __init__(self, _id):
        CapBaseObject.__init__(self, unicode(_id))

        self.add_field('title', basestring)
        self.add_field('url', basestring)
        self.add_field('ext', basestring)
        self.add_field('author', basestring)
        self.add_field('description', basestring)
        self.add_field('duration', (int,long,timedelta))
        self.add_field('date', datetime)
        self.add_field('rating', (int,long,float), NotAvailable)
        self.add_field('rating_max', (int,long,float), NotAvailable)
        self.add_field('thumbnail', Thumbnail)
        self.add_field('nsfw', bool, False)

    @classmethod
    def id2url(cls, _id):
        """Overloaded in child classes provided by backends."""
        raise NotImplementedError()

    @property
    def page_url(self):
        return self.id2url(self.id)


class ICapVideo(IBaseCap):
    """
    This capability represents the ability for a website backend to provide videos.
    """
    (SEARCH_RELEVANCE,
     SEARCH_RATING,
     SEARCH_VIEWS,
     SEARCH_DATE) = range(4)

    def search_videos(self, pattern=None, sortby=SEARCH_RELEVANCE, nsfw=False, max_results=None):
        """
        Iter results of a search on a pattern. Note that if pattern is None,
        it get the latest videos.

        @param pattern  [str] pattern to search on
        @param sortby  [enum] sort by...
        @param nsfw  [bool] include non-suitable for work videos if True
        @param max_results  [int] maximum number of results to return
        """
        raise NotImplementedError()

    def get_video(self, _id):
        """
        Get a Video from an ID.

        @param _id  the video id. It can be a numeric ID, or a page url, or so.
        @return a Video object
        """
        raise NotImplementedError()

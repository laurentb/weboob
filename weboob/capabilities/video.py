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

from .base import IBaseCap, CapBaseObject, NotLoaded


__all__ = ['BaseVideo', 'ICapVideo']


class VideoThumbnail(CapBaseObject):
    def __init__(self, url):
        CapBaseObject.__init__(self, url)
        self.add_field('url', basestring, url.replace(' ', '%20'))
        self.add_field('data', str)

    def __str__(self):
        return self.url

    def __repr__(self):
        return '<Thumbnail url="%s">' % self.url

    def __iscomplete__(self):
        return self.data is not NotLoaded


class BaseVideo(CapBaseObject):
    """
    Represents a video.
    This object has to be inherited to specify how to calculate the URL of the video from its ID.
    """
    def __init__(self, _id, title=NotLoaded, url=NotLoaded, author=NotLoaded, duration=NotLoaded, date=NotLoaded,
                 rating=NotLoaded, rating_max=NotLoaded, thumbnail=NotLoaded, thumbnail_url=None, nsfw=False):
        CapBaseObject.__init__(self, unicode(_id))

        self.add_field('title', basestring, title)
        self.add_field('url', basestring, url)
        self.add_field('ext', basestring)
        self.add_field('author', basestring, author)
        self.add_field('description', basestring)
        self.add_field('duration', (int,long,timedelta), duration)
        self.add_field('date', datetime, date)
        self.add_field('rating', (int,long,float), rating)
        self.add_field('rating_max', (int,long,float), rating_max)
        self.add_field('thumbnail', VideoThumbnail, thumbnail)
        self.add_field('nsfw', bool, nsfw)

        # XXX remove this and fix all backends
        if thumbnail_url is not None and self.thumbnail is NotLoaded:
            self.thumbnail = VideoThumbnail(thumbnail_url)

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

    def iter_search_results(self, pattern=None, sortby=SEARCH_RELEVANCE, nsfw=False, max_results=None):
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

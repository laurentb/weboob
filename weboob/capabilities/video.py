# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Christophe Benz
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


from datetime import timedelta

from .base import IBaseCap, CapBaseObject, NotAvailable, StringField, Field, DateField
from weboob.tools.capabilities.thumbnail import Thumbnail


__all__ = ['BaseVideo', 'ICapVideo']


class BaseVideo(CapBaseObject):
    """
    Represents a video.

    This object has to be inherited to specify how to calculate the URL of the video from its ID.
    """

    title =         StringField('Title of video')
    url =           StringField('URL to the video file')
    ext =           StringField('Extension of video')
    author =        StringField('Author of video')
    description =   StringField('Description of video')
    duration =      Field('Duration of video', int, long, timedelta)
    date =          DateField('Date when the video has been published')
    rating =        Field('Rating of video', int, long, float, default=NotAvailable)
    rating_max =    Field('Max rating', int, long, float, default=NotAvailable)
    thumbnail =     Field('Thumbnail of video', Thumbnail)
    nsfw =          Field('Is this video Not Safe For Work', bool, default=False)

    @classmethod
    def id2url(cls, _id):
        """Overloaded in child classes provided by backends."""
        raise NotImplementedError()

    @property
    def page_url(self):
        """
        Get page URL of the video.
        """
        return self.id2url(self.id)


class ICapVideo(IBaseCap):
    """
    This capability represents the ability for a website backend to provide videos.
    """
    (SEARCH_RELEVANCE,
     SEARCH_RATING,
     SEARCH_VIEWS,
     SEARCH_DATE) = range(4)

    def search_videos(self, pattern, sortby=SEARCH_RELEVANCE, nsfw=False):
        """
        Iter results of a search on a pattern.

        :param pattern: pattern to search on
        :type pattern: str
        :param sortby: sort by... (use SEARCH_* constants)
        :param nsfw: include non-suitable for work videos if True
        :type nsfw: bool
        :rtype: iter[:class:`BaseVideo`]
        """
        raise NotImplementedError()

    def get_video(self, _id):
        """
        Get a Video from an ID.

        :param _id: the video id. It can be a numeric ID, or a page url
        :type _id: str
        :rtype: :class:`BaseVideo` or None is fot found.
        """
        raise NotImplementedError()

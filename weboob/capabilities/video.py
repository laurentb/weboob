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

class Video(object):
    def __init__(self, _id, title=u'', url=u'', author=u'', duration=0, date=None, rating=0, rating_max=0):
        self.id = _id
        self.title = title
        self.url = url
        self.author = author
        self.duration = duration
        self.date = date
        self.rating = rating
        self.rating_max = rating_max

class ICapVideoProvider(ICap):
    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

    def get_video(self, _id):
        """
        Get a Video from an ID.

        @param _id  the video id. It can be a numeric ID, or a page url, or so.
        @return  a Video object
        """
        raise NotImplementedError()

    # XXX deprecated
    def get_video_title(self, page_url):
        raise NotImplementedError()

    # XXX deprecated
    def get_video_url(self, page_url):
        raise NotImplementedError()

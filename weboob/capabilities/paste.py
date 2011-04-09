# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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


from .base import IBaseCap, CapBaseObject, NotLoaded


__all__ = ['BasePaste', 'ICapPaste']


class BasePaste(CapBaseObject):
    """
    Represents a pasted text.
    """
    def __init__(self, _id, title=NotLoaded, language=NotLoaded, contents=NotLoaded):
        CapBaseObject.__init__(self, unicode(_id))

        self.add_field('title', basestring, title)
        self.add_field('language', basestring, language)
        self.add_field('contents', basestring, contents)

    @classmethod
    def id2url(cls, _id):
        """Overloaded in child classes provided by backends."""
        raise NotImplementedError()

    @property
    def page_url(self):
        return self.id2url(self.id)


class ICapPaste(IBaseCap):
    """
    This capability represents the ability for a website backend to store text.
    """

    def get_paste(self, _id):
        """
        Get a Video from an ID.

        @param _id  the video id. It can be a numeric ID, or a page url, or so.
        @return a Video object
        """
        raise NotImplementedError()

    def post_message(self, paste):
        """
        Post a paste.

        @param paste  Paste object
        @return
        """
        raise NotImplementedError()

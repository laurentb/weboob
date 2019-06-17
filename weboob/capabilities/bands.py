# -*- coding: utf-8 -*-

# Copyright(C) 2018 Quentin Defenouillere
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from datetime import datetime, date

from weboob.tools.compat import basestring, unicode

from .base import Capability, BaseObject, Field, StringField, UserError, NotLoaded
from .date import DateField


__all__ = ['Bandinfo', 'Band', 'Albums', 'BandNotFound', 'CapBands']


class Bandsearch(BaseObject):
    """
    Bands search.
    """
    name =                  StringField('Name of band')
    short_description =     StringField('Short description of the band')

    def __init__(self, id='', name=None, short_description=None, url=None):
        super(Bandsearch, self).__init__(id, url)
        self.name = name
        self.short_description = short_description


class BandNotFound(UserError):
    """
    Raised when no band is found.
    """
    pass


class Bandinfo(BaseObject):
    """
    Information about one specific band.
    """
    name =             StringField('Name of band')
    genre =            StringField('Music genre of the band')
    year =             StringField('Year of creation')
    country =          StringField('Country of origin')
    description =      StringField('Description of the band')

    def __init__(self, name=None, year=None, country=None, genre=None, description=None, url=None):
        super(Bandinfo, self).__init__(id, url)
        self.name = name
        self.genre = genre
        self.year = year
        self.description = description
        self.country = country


class Albums(BaseObject):
    """
    Information about one specific band.
    """
    name =             StringField('Album name')
    album_type =       StringField('Type of album')
    year =             StringField('Year of release')
    reviews =          StringField('Album reviews')

    def __init__(self, name=None, album_type=None, year=None, reviews=None, url=None):
        super(Albums, self).__init__(id, url)
        self.name = name
        self.album_type = album_type
        self.year = year
        self.reviews = reviews


class Favorites(BaseObject):
    """
    Fetch your favorite bands.
    """
    name =                  StringField('Name of favorite band')
    band_url =              StringField('URL of the favorite band')
    short_description =     StringField('Short description of the favorite band')

    def __init__(self, id='', name=None, band_url=None, short_description=None):
        super(Favorites, self).__init__(id, name)
        self.name = name
        self.band_url = band_url
        self.short_description = short_description


class Suggestions(BaseObject):
    """
    Band suggestions based on your favorite bands.
    """
    name =                  StringField('Name of suggested band')
    description =           StringField('Band description')
    url =                   StringField('URL of suggested band')

    def __init__(self, id='', name=None, description=None, url=None):
        super(Suggestions, self).__init__(id, url)
        self.name = name
        self.url = url
        self.description = description


class CapBands(Capability):
    """
    Capability to get band information on music websites.
    """

    def iter_band_search(self):
        """
        Look for a band.
        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`Bandsearch`]
        """
        raise NotImplementedError()


    def get_info(self):
        """
        Get band info.
        :param band_id: ID of the band
        :rtype: :class:`Bandinfo`
        """
        raise NotImplementedError()


    def get_albums(self):
        """
        Get a band's discography.

        :rtype: iter[:class:`Albums`]
        """
        raise NotImplementedError()


    def get_favorites(self):
        """
        Get my favorite bands.

        :rtype: iter[:class:`Favorites`]
        """
        raise NotImplementedError()


    def suggestions(self):
        """
        Get band suggestions according to your favorite bands.

        :rtype: iter[:class:`Suggestions`]
        """
        raise NotImplementedError()

# -*- coding: utf-8 -*-

# Copyright(C) 2013 Pierre Mazière
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

from .image import BaseImage
from .base import Field, StringField
from .file import ICapFile, BaseFile


__all__ = ['BaseAudio', 'ICapAudio']


class BaseAudio(BaseFile):
    """
    Represent an audio file
    """
    duration =  Field('file duration', int, long, timedelta)
    bitrate =   Field('file bit rate in Kbps', int)
    format =    StringField('file format')
    thumbnail = Field('Image associated to the file', BaseImage)


class ICapAudio(ICapFile):
    """
    Audio file provider
    """
    def search_audio(self, pattern, sortby=ICapFile.SEARCH_RELEVANCE):
        """
        search for a audio file

        :param pattern: pattern to search on
        :type pattern: str
        :param sortby: sort by ...(use SEARCH_* constants)
        :rtype: iter[:class:`BaseAudio`]
        """
        return self.search_file(pattern, sortby)

    def get_audio(self, id):
        """
        Get an audio file from an ID.

        :param id: audio file ID
        :type id: str
        :rtype: :class:`BaseAudio`]
        """
        return self.get_file(id)

# -*- coding: utf-8 -*-

# Copyright(C) 2009-2015  Bezleputh
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

from weboob.browser.filters.standard import Format


class AlbumIdFilter(Format):
    """
    Filter that help to fill Albums id field
    """
    def __init__(self, *args):
        super(AlbumIdFilter, self).__init__(u'album.%s', *args)


class PlaylistIdFilter(Format):
    """
    Filter that help to fill Albums id field
    """
    def __init__(self, *args):
        super(PlaylistIdFilter, self).__init__(u'playlist.%s', *args)


class BaseAudioIdFilter(Format):
    """
    Filter that help to fill Albums id field
    """
    def __init__(self, *args):
        super(BaseAudioIdFilter, self).__init__(u'audio.%s', *args)

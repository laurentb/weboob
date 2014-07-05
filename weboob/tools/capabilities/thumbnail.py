# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon, Noé Rubinstein
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

from weboob.capabilities.base import BaseObject, NotLoaded, StringField, BytesField


__all__ = ['Thumbnail']


class Thumbnail(BaseObject):
    """
    Thumbnail of an image.
    """

    url =   StringField('URL to photo thumbnail')
    data =  BytesField('Data')

    def __init__(self, url):
        BaseObject.__init__(self, url)
        self.url = url.replace(u' ', u'%20')

    def __str__(self):
        return self.url

    def __repr__(self):
        return '<Thumbnail url="%s">' % self.url

    def __iscomplete__(self):
        return self.data is not NotLoaded

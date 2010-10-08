# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from .base import IBaseCap, NotLoaded, CapBaseObject


__all__ = ['Emission', 'Stream', 'Radio', 'ICapRadio']


class Emission(CapBaseObject):
    FIELDS = ('artist', 'title')

    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.artist = NotLoaded
        self.title = NotLoaded

    def __iscomplete__(self):
        # This volatile information may be reloaded everytimes.
        return False

    def __unicode__(self):
        return u'%s - %s' % (self.artist, self.title)

class Stream(CapBaseObject):
    FIELDS = ('title', 'url')

    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.title = NotLoaded
        self.url = NotLoaded

    def __unicode__(self):
        return u'%s (%s)' % (self.title, self.url)

    def __repr__(self):
        return self.__unicode__()

class Radio(CapBaseObject):
    FIELDS = ('title', 'description', 'current', 'streams')

    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.title = NotLoaded
        self.description = NotLoaded
        self.streams = NotLoaded
        self.current = NotLoaded

class ICapRadio(IBaseCap):
    def iter_radios(self):
        raise NotImplementedError()

    def iter_radios_search(self, pattern):
        raise NotImplementedError()

    def get_radio(self, id):
        raise NotImplementedError()

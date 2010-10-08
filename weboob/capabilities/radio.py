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


from .base import IBaseCap, CapBaseObject


__all__ = ['Emission', 'Stream', 'Radio', 'ICapRadio']


class Emission(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('artist', unicode)
        self.add_field('title', unicode)

    def __iscomplete__(self):
        # This volatile information may be reloaded everytimes.
        return False

    def __unicode__(self):
        return u'%s - %s' % (self.artist, self.title)

class Stream(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('title', unicode)
        self.add_field('url', unicode)

    def __unicode__(self):
        return u'%s (%s)' % (self.title, self.url)

    def __repr__(self):
        return self.__unicode__()

class Radio(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('title', unicode)
        self.add_field('description', unicode)
        self.add_field('current', Emission)
        self.add_field('streams', list)

class ICapRadio(IBaseCap):
    def iter_radios(self):
        raise NotImplementedError()

    def iter_radios_search(self, pattern):
        raise NotImplementedError()

    def get_radio(self, id):
        raise NotImplementedError()

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
        if self.artist:
            return u'%s - %s' % (self.artist, self.title)
        else:
            return self.title

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
    def iter_radios_search(self, pattern):
        raise NotImplementedError()

    def get_radio(self, id):
        raise NotImplementedError()

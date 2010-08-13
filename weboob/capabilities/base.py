# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon
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


from weboob.tools.misc import iter_fields


__all__ = ['IBaseCap', 'NotAvailable', 'NotLoaded', 'CapBaseObject']


class NotAvailableMeta(type):
    def __str__(self):
        return unicode(self).decode('utf-8')

    def __unicode__(self):
        return u'Not available'

    def __nonzero__(self):
        return False


class NotAvailable(object):
    __metaclass__ = NotAvailableMeta


class NotLoadedMeta(type):
    def __str__(self):
        return unicode(self).decode('utf-8')

    def __unicode__(self):
        return u'Not loaded'

    def __nonzero__(self):
        return False


class NotLoaded(object):
    __metaclass__ = NotLoadedMeta


class IBaseCap(object):
    pass

class CapBaseObject(object):
    FIELDS = None

    def __init__(self, id, backend=None):
        self.id = id
        self.backend = backend

    def iter_fields(self):
        if self.FIELDS is None:
            for key, value in iter_fields(self):
                if key != 'backend':
                    yield key, value
        else:
            yield 'id', self.id
            for attrstr in self.FIELDS:
                yield attrstr, getattr(self, attrstr)

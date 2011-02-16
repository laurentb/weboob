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
from datetime import datetime

class Content(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('title', basestring)
        self.add_field('author', basestring)
        self.add_field('content', basestring)
        self.add_field('revision', basestring)

class Revision(CapBaseObject):
    def __init__(self, _id):
        CapBaseObject.__init__(self, _id)
        self.add_field('author', basestring)
        self.add_field('comment', basestring)
        self.add_field('revision', basestring)
        self.add_field('timestamp', datetime)
        self.add_field('minor', bool)
        


class ICapContent(IBaseCap):
    def get_content(self, id, revision=None):
        raise NotImplementedError()

    def iter_revisions(self, id):
        raise NotImplementedError()

    def push_content(self, content, message=None, minor=False):
        raise NotImplementedError()
    
    def get_content_preview(self, content):
        raise NotImplementedError()

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

    def iter_revisions(self, id, max_results=10):
        raise NotImplementedError()

    def push_content(self, content, message=None, minor=False):
        raise NotImplementedError()

    def get_content_preview(self, content):
        raise NotImplementedError()

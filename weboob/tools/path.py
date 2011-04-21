# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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
import urllib
import posixpath
import copy

class Path(object):
    def __init__(self):
        self._working_path = []
        self._previous = self._working_path


    def extend(self, user_input):

        user_input = urllib.quote_plus(user_input)
        user_input = posixpath.normpath(user_input)

        escape = lambda s: s.replace('/', '%2F')
        current_path = map(escape, self._working_path)

        abspath =  posixpath.normpath(posixpath.join('/' + '/'.join(current_path), user_input))

        abspath = abspath.split('/')[1:]
        while len(abspath) > 0 and abspath[0] == u'': del abspath[0]

        final_parse = map(urllib.unquote_plus, abspath)

        self._previous = self._working_path

        if len(final_parse) == 0:
            self._working_path = []

        self._working_path = final_parse

    def restore(self):
        self._working_path = self._previous


    def get(self):
        return copy.copy(self._working_path)

    def fromstring(self, path):
        if path[0] == '/':
            path = path[1:]
        escape = lambda s: s.replace('\/', '/')
        self._working_path = map(escape, path.split('/'))

    def tostring(self):
        escape = lambda s: s.replace('/', '\/')
        path = map(escape, self._working_path)
        return '/' + '/'.join(path)

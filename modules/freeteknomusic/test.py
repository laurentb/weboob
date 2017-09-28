# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.capabilities.audio import BaseAudio
from weboob.tools.test import BackendTest


class FreeteknomusicTest(BackendTest):
    MODULE = 'freeteknomusic'

    def test_ls(self):
        colls = list(self.backend.iter_resources([BaseAudio], []))
        assert colls
        assert colls[0].id
        assert colls[0].title
        assert colls[0].split_path
        assert colls[0].url

        files = list(self.backend.iter_resources([BaseAudio], colls[0].split_path))
        assert files
        assert files[0].id
        assert files[0].title
        assert files[0].ext
        assert files[0].url

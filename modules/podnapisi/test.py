# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

from weboob.tools.test import BackendTest

from random import choice


class PodnapisiTest(BackendTest):
    MODULE = 'podnapisi'

    def test_subtitle(self):
        lsub = []
        subtitles = self.backend.iter_subtitles('fr', 'spiderman')
        for subtitle in subtitles:
            lsub.append(subtitle)
        assert (len(lsub) > 0)

        # get the file of a random sub
        if len(lsub):
            subtitle = choice(lsub)
            assert(not self.backend.get_subtitle_file(subtitle.id).startswith(b'<'))
            ss = self.backend.get_subtitle(subtitle.id)
            assert ss.url.startswith('https')

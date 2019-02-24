# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.capabilities.collection import Collection
from weboob.capabilities.video import BaseVideo
from weboob.tools.test import BackendTest, skip_without_config


class FunmoocTest(BackendTest):
    MODULE = 'funmooc'

    @skip_without_config('email', 'password')
    def test_basic(self):
        basic_id = 'FUN-00101-Trimestre_3_2014'

        courses = list(self.backend.iter_resources([BaseVideo], []))
        for course in courses:
            self.assertIsInstance(course, Collection)
            if course.split_path == [basic_id]:
                break
        else:
            assert False, 'The default course was not found'

        videos = list(self.backend.iter_resources_flat([BaseVideo], [basic_id]))
        for video in videos:
            self.assertTrue(video)
            self.assertIsInstance(video, BaseVideo)
            self.assertTrue(video.id)
            self.assertTrue(video.url)
            self.assertTrue(video.title)

        self.assertTrue(self.backend.browser.open(video.url, method='HEAD'))

    @skip_without_config('email', 'password')
    def test_search(self):
        video = next(self.backend.search_videos('Tester le lecteur HTML 5'))
        self.assertTrue(video)
        self.assertIsInstance(video, BaseVideo)
        self.assertTrue(video.id)
        self.assertTrue(video.url)
        self.assertTrue(video.title)

        videos = list(self.backend.search_videos('Bienvenue sur FUN'))
        self.assertTrue(videos)
        for video in videos:
            self.assertTrue(video)
            self.assertIsInstance(video, BaseVideo)
            self.assertTrue(video.id)
            self.assertTrue(video.url)
            self.assertTrue(video.title)

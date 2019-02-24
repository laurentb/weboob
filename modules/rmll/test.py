# -*- coding: utf-8 -*-

# Copyright(C) 2015 Guilhem Bonnefille
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


from weboob.tools.test import BackendTest
from weboob.capabilities.video import BaseVideo


class RmllTest(BackendTest):
    MODULE = 'rmll'

    def test_video_search(self):
        videos = self.backend.search_videos('test')
        self.assertTrue(videos)
        for video in videos:
            self.assertTrue(video.id, 'ID for video not found')

    def test_video_page(self):
        for slug in ["v124f0bc409e704d92cf", "%s/permalink/v124f0bc409e704d92cf/" % self.backend.browser.BASEURL]:
            video = self.backend.browser.get_video(slug)
            self.assertTrue(video.id, 'ID for video not found')
            self.assertTrue(video.url, 'URL for video "%s" not found' % (video.id))
            self.assertTrue(video.thumbnail, 'Thumbnail for video "%s" not found' % (video.id))
            self.assertTrue(video.title, 'Title for video "%s" not found' % (video.id))
            # self.assertTrue(video.description, 'Description for video "%s" not found' % (video.id))
            self.assertTrue(video.duration, 'Duration for video "%s" not found' % (video.id))
            # help(video)

    def test_video_fill(self):
        slug = "v124f0bc409e704d92cf"
        video = self.backend.browser.get_video(slug)
        video = self.backend.fill_video(video, ["url"])
        self.assertTrue(video)
        self.assertTrue(video.url, 'URL for video "%s" not found' % (video.id))

    def test_browse(self):
        for path in [[], ['latest']]:
            videos = self.backend.iter_resources([BaseVideo], path)
            self.assertTrue(videos)
            for video in videos:
                self.assertTrue(video.id, 'ID for video not found')

    def test_missing_duration(self):
        videos = self.backend.search_videos('weboob')
        self.assertTrue(videos)
        for video in videos:
            self.assertTrue(video.id, 'ID for video not found')
            video = self.backend.fill_video(video, ["$full"])

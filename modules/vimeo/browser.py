# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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


from weboob.browser import PagesBrowser, URL
from weboob.browser.exceptions import HTTPNotFound
from .pages import SearchPage, VideoPage, VideoJsonPage, CategoriesPage, ChannelsPage

import urllib

__all__ = ['VimeoBrowser']


class VimeoBrowser(PagesBrowser):

    BASEURL = 'http://vimeo.com'

    search_page = URL(r'search/page:(?P<page>.*)/sort:(?P<sortby>.*)/format:thumbnail\?type=videos&q=(?P<pattern>.*)',
                      r'channels/(?P<channel>.*)/videos/.*?',
                      r'categories/(?P<category>.*)/videos/.*?',
                      SearchPage)

    categories_page = URL('categories', CategoriesPage)
    channels_page = URL('channels', ChannelsPage)

    video_url = URL(r'http://player.vimeo.com/video/(?P<_id>.*)/config', VideoJsonPage)
    video_page = URL('http://vimeo.com/(?P<_id>.*)', VideoPage)

    def get_video(self, _id, video=None):
        try:
            video = self.video_page.go(_id=_id).get_video(video)
            return self.video_url.open(_id=_id).fill_url(obj=video)
        except HTTPNotFound:
            return None

    def search_videos(self, pattern, sortby):
        return self.search_page.go(pattern=urllib.quote_plus(pattern.encode('utf-8')),
                                   sortby=sortby,
                                   page=1).iter_videos()

    def get_categories(self):
        return self.categories_page.go().iter_categories()

    def get_channels(self):
        return self.channels_page.go().iter_channels()

    def get_channel_videos(self, channel):
        return self.search_page.go(channel=channel).iter_videos()

    def get_category_videos(self, category):
        return self.search_page.go(category=category).iter_videos()

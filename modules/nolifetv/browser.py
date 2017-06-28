# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.tools.compat import urlencode

from weboob.deprecated.browser.decorators import id2url
from .video import NolifeTVVideo
from .pages import VideoPage, VideoListPage, FamilyPage, AboPage, LoginPage, HomePage

__all__ = ['NolifeTVBrowser']


class NolifeTVBrowser(Browser):
    USER_AGENT = Browser.USER_AGENTS['desktop_firefox']
    DOMAIN = 'mobile.nolife-tv.com'
    PROTOCOL = 'http'
    PAGES = { r'http://mobile.nolife-tv.com/online/familles-\w+/': FamilyPage,
              r'http://mobile.nolife-tv.com/online/emission-(?P<id>\d+)/': VideoPage,
              'http://mobile.nolife-tv.com/do.php': VideoListPage,
              'http://mobile.nolife-tv.com/online/': VideoListPage,
              'http://mobile.nolife-tv.com/abonnement/': AboPage,
              'http://mobile.nolife-tv.com/login': LoginPage,
              'http://mobile.nolife-tv.com/': HomePage,
              }
    AVAILABLE_VIDEOS = ['[Gratuit]']

    def is_logged(self):
        return (self.username is None or (not self.is_on_page(HomePage)) or self.page.is_logged())

    def login(self):
        if self.username is None:
            return

        if not self.is_on_page(LoginPage):
            self.location('/login', no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        self.location('/abonnement/', no_login=True)
        assert self.is_on_page(AboPage)

        self.AVAILABLE_VIDEOS = self.page.get_available_videos()

    @id2url(NolifeTVVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage)

        return self.page.get_video(video)

    def iter_family(self, type, sub):
        self.location('/online/familles-%s/' % type)
        assert self.is_on_page(FamilyPage)

        return self.page.iter_family(sub)

    def iter_category(self, type):
        self.location('/online/familles-%s/' % type)
        assert self.is_on_page(FamilyPage)

        return self.page.iter_category()

    def iter_video(self, family):
        data = { 'a': 'ge',
                 'famille': family,
                 'emissions': 0 }

        while True:
            self.location('/do.php', urlencode(data))
            assert self.is_on_page(VideoListPage)

            if self.page.is_list_empty():
                break

            for vid in self.page.iter_video(self.AVAILABLE_VIDEOS):
                yield vid
            data['emissions'] = data['emissions'] + 1

    def get_latest(self):
        return self.iter_video(0)

    def search_videos(self, pattern):
        data = { 'search': pattern,
                 'submit': 'Rechercher' }
        self.location('/online/', urlencode(data))
        assert self.is_on_page(VideoListPage)

        for vid in self.page.iter_video(self.AVAILABLE_VIDEOS):
            yield vid

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


import urllib

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.tools.browser.decorators import id2url

from .pages.index import IndexPage
from .pages.video import VideoPage
from .video import NolifeTVVideo


__all__ = ['NolifeTVBrowser']


class NolifeTVBrowser(BaseBrowser):
    DOMAIN = 'online.nolife-tv.com'
    ENCODING = None
    PAGES = {r'http://online.nolife-tv.com/index.php\??': IndexPage,
             r'http://online.nolife-tv.com/': IndexPage,
             r'http://online.nolife-tv.com/index.php\?id=(?P<id>.+)': VideoPage}

    def is_logged(self):
        if self.password is None:
            return True

        login = self.page.document.getroot().cssselect('div#form_login')
        return len(login) == 0

    def login(self):
        if self.password is None:
            return

        params = {'cookieuser':        1,
                  'do':                'login',
                  'securitytoken':     'guest',
                  'vb_login_username': self.username,
                  'vb_login_password': self.password,
                 }

        self.readurl('http://forum.nolife-tv.com/login.php?do=login', urllib.urlencode(params))

        self.location('/', no_login=True)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    @id2url(NolifeTVVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage), 'Should be on video page.'
        return self.page.get_video(video)

    def search_videos(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location('/index.php?', 'search=%s' % urllib.quote_plus(pattern.encode('utf-8')))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

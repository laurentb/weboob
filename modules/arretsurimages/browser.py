# -*- coding: utf-8 -*-

# Copyright(C) 2013      franek
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
from weboob.deprecated.browser.decorators import id2url

from .pages import VideoPage, IndexPage, LoginPage, LoginRedirectPage
from .video import ArretSurImagesVideo


__all__ = ['ArretSurImagesBrowser']


class ArretSurImagesBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.arretsurimages.net'
    ENCODING = None

    PAGES = {
        '%s://%s/contenu.php\?id=.+' % (PROTOCOL, DOMAIN): VideoPage,
        '%s://%s/emissions.php' % (PROTOCOL, DOMAIN): IndexPage,
        '%s://%s/forum/login.php' % (PROTOCOL, DOMAIN): LoginPage,
        '%s://%s/forum/index.php' % (PROTOCOL, DOMAIN): LoginRedirectPage,
    }

    def home(self):
        self.location('http://www.arretsurimages.net')

    def search_videos(self, pattern):
        self.location(self.buildurl('/emissions.php'))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos(pattern)

    @id2url(ArretSurImagesVideo.id2url)
    def get_video(self, url, video=None):
        self.login()
        self.location(url)
        return self.page.get_video(video)

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.location('http://www.arretsurimages.net/forum/login.php', no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def latest_videos(self):
        self.location(self.buildurl('/emissions.php'))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

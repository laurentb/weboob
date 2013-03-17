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

import urllib

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.browser.decorators import id2url

#from .pages.index import IndexPage
from .pages import VideoPage, IndexPage
from .video import GDCVaultVideo


__all__ = ['GDCVaultBrowser']


class GDCVaultBrowser(BaseBrowser):
    DOMAIN = 'gdcvault.com'
    ENCODING = 'utf-8'
    PAGES = {r'http://[w\.]*gdcvault.com/play/(?P<id>[\d]+)/?.*': VideoPage,
             r'http://[w\.]*gdcvault.com/': IndexPage,
            }

    def is_logged(self):
        if self.password is None:
            return True

        if not self.page:
            return False

        obj = self.parser.select(self.page.document.getroot(), 'h3[id=welcome_user_name]', 1)
        if obj is None:
            return False

        return obj.attrib.get('class','') != "hidden"

    def login(self):
        if self.password is None:
            return

        params = {'remember_me': 0,
                  'email':       self.username,
                  'password':    self.password,
                 }

        data = self.readurl('http://gdcvault.com/api/login.php',
                            urllib.urlencode(params))
        # data is returned as JSON, not sure yet if it's useful

        print data
        if data is None:
            raise BrowserBanned('Too many open sessions?')

        self.location('/', no_login=True)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def close_session(self):
        print "logging out..."
        self.openurl('/logout', '')

    @id2url(GDCVaultVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        # redirects to /login means the video is not public
        if not isinstance(self.page, VideoPage):
            raise BrowserUnavailable('Requires account')
        return self.page.get_video(video)

    # def search_videos(self, pattern, sortby):
    #     return None
    #     self.location(self.buildurl('http://gdcvault.com/en/search%s' % sortby, query=pattern.encode('utf-8')))
    #     assert self.is_on_page(IndexPage)
    #     return self.page.iter_videos()

    # def latest_videos(self):
    #     self.home()
    #     assert self.is_on_page(IndexPage)
    #     return self.page.iter_videos()

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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrowserUnavailable,\
        BrowserBanned
from weboob.deprecated.browser.decorators import id2url
from weboob.tools.compat import urlencode

#from .pages.index import IndexPage
from .pages import VideoPage, IndexPage, SearchPage
from .video import GDCVaultVideo
#HACK
from urllib2 import HTTPError
import re
from weboob.capabilities.base import NotAvailable


__all__ = ['GDCVaultBrowser']


class GDCVaultBrowser(Browser):
    DOMAIN = 'gdcvault.com'
    ENCODING = 'utf-8'
    PAGES = {r'http://[w\.]*gdcvault.com/play/(?P<id>[\d]+)/?.*': VideoPage,
             r'http://[w\.]*gdcvault.com/search\.php.*': (SearchPage, "json"),
             r'http://[w\.]*gdcvault.com/.*': IndexPage,
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
                            urlencode(params))
        # some data returned as JSON, not sure yet if it's useful

        if data is None:
            self.openurl('/logout', '')
            raise BrowserBanned('Too many open sessions?')

        self.location('/', no_login=True)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def close_session(self):
        if self.password is None or not self.is_logged():
            return

        self.openurl('/logout', '')

    @id2url(GDCVaultVideo.id2url)
    def get_video(self, url, video=None):
        requires_account = False
        redir_url = None

        # FIXME: this is quite ugly
        # but is required to handle cases like 1013422@gdcvault
        self.set_handle_redirect(False)
        try:
            self.open_novisit(url)
            #headers = req.info()
        except HTTPError as e:
            if e.getcode() == 302 and hasattr(e, 'hdrs'):
                if e.hdrs['Location'] in ['/', '/login']:
                    requires_account = True
                else:
                    # 1015865 redirects to a file with an eacute in the name
                    redir_url = unicode(e.hdrs['Location'], encoding='utf-8')
        self.set_handle_redirect(True)

        if requires_account:
            raise BrowserUnavailable('Requires account')

        if redir_url:
            if video is None:
                m = re.match('http://[w\.]*gdcvault.com/play/(?P<id>[\d]+)/?.*', url)
                if m:
                    video = GDCVaultVideo(int(m.group(1)))
                else:
                    raise BrowserUnavailable('Cannot find ID on page with redirection')
            video.url = redir_url
            video.set_empty_fields(NotAvailable)
            # best effort for now
            return video

        self.location(url)
        # redirects to /login means the video is not public
        if not self.is_on_page(VideoPage):
            raise BrowserUnavailable('Requires account')
        return self.page.get_video(video)

    def search_videos(self, pattern, sortby):
        post_data = {"firstfocus" : "",
                     "category" : "free",
                     "keyword" : pattern.encode('utf-8'),
                     "conference_id" : "", }
        post_data = urlencode(post_data)
        # probably not required
        self.addheaders = [('Referer', 'http://gdcvault.com/'),
                           ("Content-Type" , 'application/x-www-form-urlencoded') ]

        # is_logged assumes html page
        self.location('http://gdcvault.com/search.php',
                      data=post_data, no_login=True)

        assert self.is_on_page(SearchPage)
        return self.page.iter_videos()

    def latest_videos(self):
        #self.home()
        self.location('/free')
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backend import Backend
from weboob.capabilities.video import ICapVideoProvider

from .browser import YoutubeBrowser

class YoutubeBackend(Backend, ICapVideoProvider):
    NAME = 'youtube'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.1'
    DESCRIPTION = 'Youtube videos website'
    LICENSE = 'GPLv3'

    CONFIG = {}
    browser = None

    def need_browser(func):
        def inner(self, *args, **kwargs):
            if not self.browser:
                self.browser = YoutubeBrowser()
            return func(self, *args, **kwargs)
        return inner

    @need_browser
    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

    @need_browser
    def get_video_title(self, page_url):
        return self.browser.get_video_title(page_url)

    @need_browser
    def get_video_url(self, page_url):
        return self.browser.get_video_url(page_url)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Romain Bignon
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


from weboob.tools.browser import BaseBrowser

from .pages import BaseYoutubePage, VideoPage, ForbiddenVideoPage, \
                   VerifyAgePage, VerifyControversyPage, \
                   LoginPage, LoginRedirectPage


__all__ = ['YoutubeBrowser']


class YoutubeBrowser(BaseBrowser):
    DOMAIN = u'youtube.com'
    ENCODING = 'utf-8'
    PAGES = {r'https?://.*youtube\.com/': BaseYoutubePage,
             r'https?://.*youtube\.com/watch\?v=(?P<id>.+)': VideoPage,
             r'https?://.*youtube\.com/index\?ytsession=.+': ForbiddenVideoPage,
             r'https?://.*youtube\.com/verify_age\?next_url=(?P<next_url>.+)': VerifyAgePage,
             r'https?://.*youtube\.com/verify_controversy\?next_url(?P<next_url>.+)': VerifyControversyPage,
             r'https?://accounts.google.com/ServiceLogin.*': LoginPage,
             r'https?://accounts.google.fr/accounts/SetSID.*': LoginRedirectPage,
            }

    def is_logged(self):
        logged = not self.is_on_page(BaseYoutubePage) or self.page.is_logged()
        return logged

    def login(self):
        self.location('https://accounts.google.com/ServiceLogin?uilel=3&service=youtube&passive=true&continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26nomobiletemp%3D1%26hl%3Den_US%26next%3D%252F&hl=en_US&ltmpl=sso')
        self.page.login(self.username, self.password)

    def get_video_url(self, video, player_url):
        self.location(player_url + '&has_verified=1')

        assert self.is_on_page(VideoPage)
        return self.page.get_video_url(video)

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

import re

from weboob.capabilities.base import UserError
from weboob.capabilities.image import BaseImage
from weboob.deprecated.browser import Page, BrokenPageError
from weboob.capabilities import NotAvailable


from .video import ArretSurImagesVideo


class IndexPage(Page):
    def iter_videos(self, pattern=None):
        videos = self.document.getroot().cssselect("div[class=bloc-contenu-8]")
        for div in videos:
            title = self.parser.select(div, 'h1', 1).text_content().replace('  ', ' ')
            if pattern:
                if pattern.upper() not in title.upper():
                    continue
            m = re.match(r'/contenu.php\?id=(.*)', div.find('a').attrib['href'])
            _id = ''
            if m:
                _id = m.group(1)

            video = ArretSurImagesVideo(_id)
            video.title = unicode(title)
            video.rating = None
            video.rating_max = None

            thumb = self.parser.select(div, 'img', 1)
            url = u'http://www.arretsurimages.net' + thumb.attrib['src']
            video.thumbnail = BaseImage(url)
            video.thumbnail.url = video.thumbnail.id

            yield video


class ForbiddenVideo(UserError):
    pass


class VideoPage(Page):
    def is_logged(self):
        try:
            self.parser.select(self.document.getroot(), '#user-info', 1)
        except BrokenPageError:
            return False
        else:
            return True

    def on_loaded(self):
        if not self.is_logged():
            raise ForbiddenVideo('This video or group may contain content that is inappropriate for some users')

    def get_video(self, video=None):
        if not video:
            video = ArretSurImagesVideo(self.get_id())
        video.title = unicode(self.get_title())
        video.url = unicode(self.get_url())
        video.set_empty_fields(NotAvailable)
        return video

    def get_firstUrl(self):
        obj = self.parser.select(self.document.getroot(), 'a.bouton-telecharger', 1)
        firstUrl = obj.attrib['href']
        return firstUrl

    def get_title(self):
        title = self.document.getroot().cssselect('div[id=titrage-contenu] h1')[0].text
        return title

    def get_id(self):
        m = re.match(r'http://videos.arretsurimages.net/telecharger/(.*)', self.get_firstUrl())
        if m:
            return m.group(1)
        self.logger.warning('Unable to parse ID')
        return 0

    def get_url(self):
        firstUrl = self.get_firstUrl()
        doc = self.browser.get_document(self.browser.openurl(firstUrl))
        links = doc.xpath('//a')
        url = None
        i = 1
        for link in links:
            # we take the second link of the page
            if i == 2:
                url = link.attrib['href']
            i += 1
        return url


class LoginPage(Page):
    def login(self, username, password):
        response = self.browser.response()
        response.set_data(response.get_data().replace("<br/>", "<br />"))  # Python mechanize is broken, fixing it.
        self.browser.set_response(response)
        self.browser.select_form(nr=0)
        self.browser.form.set_all_readonly(False)
        self.browser['redir'] = '/forum/index.php'
        self.browser['username'] = username
        self.browser['password'] = password
        self.browser.submit()


class LoginRedirectPage(Page):
    pass

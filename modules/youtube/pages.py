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


from urlparse import parse_qsl

from weboob.capabilities.base import UserError
from weboob.tools.browser import BasePage, BrokenPageError, BrowserIncorrectPassword
from weboob.tools.json import json


__all__ = ['LoginPage', 'LoginRedirectPage', 'ForbiddenVideo', 'ForbiddenVideoPage',
           'VerifyAgePage', 'VerifyControversyPage', 'VideoPage']


class LoginPage(BasePage):
    def on_loaded(self):
        errors = []
        for errdiv in self.parser.select(self.document.getroot(), 'div.errormsg'):
            errors.append(errdiv.text.encode('utf-8').strip())

        if len(errors) > 0:
            raise BrowserIncorrectPassword(', '.join(errors))

    def login(self, username, password):
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'gaia_loginform')
        self.browser['Email'] = username
        self.browser['Passwd'] = password
        self.browser.submit()


class LoginRedirectPage(BasePage):
    pass


class ForbiddenVideo(UserError):
    pass


class BaseYoutubePage(BasePage):
    def is_logged(self):
        try:
            self.parser.select(self.document.getroot(), 'span#yt-masthead-user-displayname', 1)
        except BrokenPageError:
            return False
        else:
            return True


class ForbiddenVideoPage(BaseYoutubePage):
    def on_loaded(self):
        element = self.parser.select(self.document.getroot(), '.yt-alert-content', 1)
        raise ForbiddenVideo(element.text.strip())


class VerifyAgePage(BaseYoutubePage):
    def on_loaded(self):
        if not self.is_logged():
            raise ForbiddenVideo('This video or group may contain content that is inappropriate for some users')

        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'confirm-age-form')
        self.browser.submit()


class VerifyControversyPage(BaseYoutubePage):
    def on_loaded(self):
        self.browser.select_form(predicate=lambda form: 'verify_controversy' in form.attrs.get('action', ''))
        self.browser.submit()


class VideoPage(BaseYoutubePage):
    AVAILABLE_FORMATS = [38, 37, 45, 22, 43, 35, 34, 18, 6, 5, 17, 13]
    FORMAT_EXTENSIONS = {
        13: '3gp',
        17: 'mp4',
        18: 'mp4',
        22: 'mp4',
        37: 'mp4',
        38: 'video',  # You actually don't know if this will be MOV, AVI or whatever
        43: 'webm',
        45: 'webm',
    }

    def get_video_url(self, format=38):
        formats = {}
        for script in self.parser.select(self.document.getroot(), 'script'):
            text = script.text
            if not text:
                continue

            pattern = "ytplayer.config = "
            pos = text.find(pattern)
            if pos < 0:
                continue

            sub = text[pos+len(pattern):].rstrip(';\n')
            a = json.loads(sub)

            for part in a['args']['url_encoded_fmt_stream_map'].split(','):
                args = dict(parse_qsl(part))
                formats[int(args['itag'])] = args['url'] + '&signature=' + args['sig']

            break

        # choose the better format to use.
        for format in self.AVAILABLE_FORMATS[self.AVAILABLE_FORMATS.index(format):]:
            if format in formats:
                url = formats.get(format)
                ext = self.FORMAT_EXTENSIONS.get(format, 'flv')
                return url, ext

        # check errors only here, in case the video url is available though
        error = self.document.xpath('//h1[@id="unavailable-message"]')
        if len(error) > 0:
            raise ForbiddenVideo(unicode(error[0].text).strip())

        raise BrokenPageError('Unable to find file URL')

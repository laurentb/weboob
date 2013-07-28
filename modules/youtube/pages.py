# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Christophe Benz, Romain Bignon, Laurent Bachelier
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

# Some parts are taken from youtube-dl, licensed under the UNLICENSE.


from urlparse import parse_qsl
import re

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
        self.browser['Email'] = username.encode(self.browser.ENCODING)
        self.browser['Passwd'] = password.encode(self.browser.ENCODING)
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

    def _decrypt_signature(self, s):
        """Turn the encrypted s field into a working signature"""

        if len(s) == 92:
            return s[25] + s[3:25] + s[0] + s[26:42] + s[79] + s[43:79] + s[91] + s[80:83]
        elif len(s) == 90:
            return s[25] + s[3:25] + s[2] + s[26:40] + s[77] + s[41:77] + s[89] + s[78:81]
        elif len(s) == 88:
            return s[48] + s[81:67:-1] + s[82] + s[66:62:-1] + s[85] + s[61:48:-1] + s[67] + s[47:12:-1] + s[3] + s[11:3:-1] + s[2] + s[12]
        elif len(s) == 87:
            return s[62] + s[82:62:-1] + s[83] + s[61:52:-1] + s[0] + s[51:2:-1]
        elif len(s) == 86:
            return s[2:63] + s[82] + s[64:82] + s[63]
        elif len(s) == 85:
            return s[2:8] + s[0] + s[9:21] + s[65] + s[22:65] + s[84] + s[66:82] + s[21]
        elif len(s) == 84:
            return s[83:36:-1] + s[2] + s[35:26:-1] + s[3] + s[25:3:-1] + s[26]
        elif len(s) == 83:
            return s[6] + s[3:6] + s[33] + s[7:24] + s[0] + s[25:33] + s[53] + s[34:53] + s[24] + s[54:]
        elif len(s) == 82:
            return s[36] + s[79:67:-1] + s[81] + s[66:40:-1] + s[33] + s[39:36:-1] + s[40] + s[35] + s[0] + s[67] + s[32:0:-1] + s[34]
        elif len(s) == 81:
            return s[6] + s[3:6] + s[33] + s[7:24] + s[0] + s[25:33] + s[2] + s[34:53] + s[24] + s[54:81]

        else:
            raise BrokenPageError(u'Unable to decrypt signature, key length %d not supported; retrying might work' % (len(s)))

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
            # json spec only allows \u - convert other escape sequences
            sub = re.sub(r'\\x([a-f0-9]{2})', r'\u\1', sub)
            sub = re.sub(r'\\U([a-f0-9]{4})([a-f0-9]{4})', r'\u\1\u\2', sub)
            a = json.loads(sub)

            for part in a['args']['url_encoded_fmt_stream_map'].split(','):
                args = dict(parse_qsl(part))
                url = args['url']
                if 'sig' in args:
                    signature = args['sig']
                elif 's' in args:
                    signature = self._decrypt_signature(args['s'])
                formats[int(args['itag'])] = args['url'] + '&signature=' + signature

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

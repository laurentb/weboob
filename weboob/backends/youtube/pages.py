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


import urllib

from weboob.tools.browser import BasePage


__all__ = ['ForbiddenVideo', 'ForbiddenVideoPage', 'VerifyAgePage', 'VideoPage']


class ForbiddenVideo(Exception):
    pass


class ForbiddenVideoPage(BasePage):
    def on_loaded(self):
        element = self.parser.select(self.document.getroot(), '.yt-alert-content', 1)
        raise ForbiddenVideo(element.text.strip())


class VerifyAgePage(BasePage):
    def on_loaded(self):
        raise ForbiddenVideo('This video or group may contain content that is inappropriate for some users')


class VideoPage(BasePage):
    AVAILABLE_FORMATS = [38, 37, 22, 45, 35, 34, 43, 18, 6, 5, 17, 13]
    FORMAT_EXTENSIONS = {
        13: '3gp',
        17: 'mp4',
        18: 'mp4',
        22: 'mp4',
        37: 'mp4',
        38: 'video', # You actually don't know if this will be MOV, AVI or whatever
        43: 'webm',
        45: 'webm',
    }

    def get_video_url(self, format=18):
        formats = {}
        for script in self.parser.select(self.document.getroot(), 'script'):
            text = script.text
            if not text:
                continue
            pos = text.find('"fmt_url_map": "')
            if pos >= 0:
                pos2 = text.find('"', pos + 17)
                fmt_map = urllib.unquote(text[pos + 17:pos2]) + ','
                parts = fmt_map.split('|')
                key = parts[0]
                for p in parts[1:]:
                    idx = p.rfind(',')
                    value = p[:idx].replace('\\/', '/').replace('\u0026', '&').replace(',', '%2C')
                    formats[int(key)] = value
                    key = p[idx + 1:]
                break
        for format in self.AVAILABLE_FORMATS[self.AVAILABLE_FORMATS.index(format):]:
            if format in formats:
                url = formats.get(format)
                ext = self.FORMAT_EXTENSIONS.get(format, 'flv')
                return url, ext

        return None, None

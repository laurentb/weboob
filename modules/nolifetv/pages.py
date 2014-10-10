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


from weboob.capabilities.collection import Collection
from weboob.capabilities.image import BaseImage

from weboob.deprecated.browser import Page

import re
from datetime import datetime, timedelta

from .video import NolifeTVVideo


class VideoPage(Page):
    def get_video(self, video):
        if not video:
            video = NolifeTVVideo(self.group_dict['id'])

        els = self.document.getroot().xpath('//div[@data-role="content"]')
        if els and els[0] is not None:
            h3 = els[0].find('h3')
            if h3 is not None and h3.text:
                video.title = unicode(h3.text)

            h4 = els[0].find('h4')
            if h4 is not None and h4.text:
                video.title = video.title + u' - ' + h4.text

            thumb = els[0].find('p/img')
            if thumb is not None and thumb.get('src'):
                video.thumbnail = BaseImage(thumb.attrib['src'])
                video.thumbnail.url = video.thumbnail.id

            ps = els[0].findall('p')
            if len(ps) > 4:
                if ps[4].text:
                    video.description = ps[4].text
                if ps[0].text and ps[0].text != u'∞':
                    video.date = datetime.strptime(ps[0].text, '%d/%m/%Y').date()

                for text in ps[2].xpath('.//text()'):
                    m = re.search(r'[^\d]*((\d+):)?(\d+)s?', text)
                    if m:
                        if m.group(2):
                            minutes = int(m.group(2))
                        else:
                            minutes = 0
                        video.duration = timedelta(minutes=minutes,
                                                   seconds=int(m.group(3)))
            return video


class VideoListPage(Page):
    def is_list_empty(self):
        return self.document.getroot() is None

    def iter_video(self, available_videos):
        for el in self.document.getroot().xpath('//li/a'):
            strongs = el.findall('p/strong')
            if len(strongs) > 3 and strongs[0].text not in ['Autopromo', 'Annonce'] and strongs[1].text in available_videos:
                m = re.search(r'emission-(\d+)', el.attrib['href'])
                if m and m.group(1):
                    video = NolifeTVVideo(m.group(1))
                    h3 = el.find('h3')
                    if h3 is not None and h3.text:
                        video.title = unicode(h3.text)
                    if strongs[3].text:
                        video.title = video.title + ' - ' + strongs[3].text
                    yield video


class FamilyPage(Page):
    def iter_category(self):
        subs = list()

        for el in self.document.xpath('//ul/li[@data-role="list-divider"]'):
            if el.text not in subs:
                yield Collection([el.text], unicode(el.text))
            subs.append(el.text)

    def iter_family(self, sub):
        for el in self.document.xpath('//ul/li[@data-role="list-divider"]'):
            if el.text != sub:
                continue

            while True:
                el = el.getnext()
                if el is None or el.get('data-role'):
                    break
                h1 = el.find('.//h1')
                id = h1.getparent().attrib['href']
                m = re.search(r'famille-(\d+)', id)
                if m and m.group(1):
                    yield Collection([m.group(1)], unicode(h1.text))


class AboPage(Page):
    def get_available_videos(self):
        available = ['[Gratuit]']

        for text in self.document.xpath('//div[@data-role="content"]/center/text()'):
            if 'Soutien' in text:
                available.append('[Archive]')
                available.append('[Standard]')
            if 'Standard' in text:
                available.append('[Standard]')

        return available


class LoginPage(Page):
    def login(self, username, password):
        self.browser.select_form(name='login')
        self.browser['username'] = str(username)
        self.browser['password'] = str(password)
        self.browser.submit()


class HomePage(Page):
    def is_logged(self):
        return len(self.document.xpath('//a[@href="deconnexion/"]')) == 1

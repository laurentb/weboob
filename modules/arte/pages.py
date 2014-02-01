# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
import HTMLParser

from weboob.tools.browser import BasePage
from weboob.capabilities import NotAvailable
from weboob.capabilities.image import BaseImage

from .video import ArteLiveVideo
from .collection import ArteLiveCollection

__all__ = ['ArteLivePage', 'ArteLiveCategorieVideoPage', 'ArteLiveVideoPage']


class ArteLiveVideoPage(BasePage):
    def get_video(self, video=None, lang='fr', quality='hd'):
        if not video:
            video = ArteLiveVideo(self.group_dict['id'])

        urls = {}
        for url in self.document.xpath('//video')[0].getchildren():
            if url.tag.startswith('url'):
                urls[url.tag[-2:]] = url.text

        if quality in urls:
            video.url = u'%s' % urls[quality]
        else:
            video.url = u'%s' % urls.popitem()[1]
        return video


class ArteLiveCategorieVideoPage(BasePage):
    def iter_videos(self, lang='fr'):
        videos = list()
        xml_url = (self.document.xpath('//link')[0]).attrib['href']
        datas = self.browser.readurl(xml_url)
        re_items = re.compile("(<item>.*?</item>)", re.DOTALL)
        items = re.findall(re_items, datas)
        for item in items:
            parsed_element = self.get_element(item, lang)
            if parsed_element:
                video = ArteLiveVideo(parsed_element['ID'])
                video.title = parsed_element['title']
                video.description = parsed_element['pitch']
                video.author = parsed_element['author']
                if parsed_element['pict']:
                    video.thumbnail = BaseImage(parsed_element['pict'])
                    video.thumbnail.url = video.thumbnail.id
                video.set_empty_fields(NotAvailable, ('url',))
                videos.append(video)
        return videos

    def get_element(self, chain, lang):
        ele = {}
        tt = re.compile("(?<=<title>)(.*?)(?=</title>)", re.DOTALL)
        lk = re.compile("(?<=<link>)(http://liveweb.arte.tv/{0}/video/.*?)"
                        "(?=</link>)".format(lang), re.DOTALL)
        dt = re.compile("(?<=<pubDate>)(.*?)(?=</pubDate>)", re.DOTALL)
        pt = re.compile("(?<=<description>)(.*?)(?=</description>)", re.DOTALL)
        at = re.compile("(?<=<author>)(.*?)(?=</author>)", re.DOTALL)
        en = re.compile("<enclosure.*?/event/.*?/(.*?)-.*?/>", re.DOTALL)
        pix = re.compile("(?<=<enclosure url=\")(.*?)(?=\" type=\"image/)", re.DOTALL)
        try:
            ele['link'] = lk.search(chain).group(0)
        except:
            return None
        try:
            ele['ID'] = int(en.search(chain).group(1))
        except:
            return None
        try:
            s = tt.search(chain).group(0)
            ele['title'] = s.decode('utf-8', 'replace')
        except:
            ele['title'] = "No title"
        try:
            s = (dt.search(chain).group(0))
            ele['date'] = s.decode('utf-8', 'replace')
        except:
            ele['date'] = "No date"
        try:
            s = (pt.search(chain).group(0))
            s = HTMLParser.HTMLParser().unescape(s)
            ele['pitch'] = HTMLParser.HTMLParser().unescape(s)
        except:
            ele['pitch'] = "No description"
        try:
            s = (at.search(chain).group(0))
            ele['author'] = s.decode('utf-8', 'replace')
        except:
            ele['author'] = "Unknow"
        try:
            ele['pict'] = pix.search(chain).group(0)
        except:
            ele['pict'] = None
        return ele


class ArteLivePage(BasePage):
    def iter_resources(self):
        items = list()
        for el in self.document.xpath('//ul[@id="categoryArray"]/li'):
            a = el.find('a')
            m = re.match(r'http://liveweb.arte.tv/*', a.attrib['href'])
            if m:
                url = u'%s' % a.attrib['href']
                _id = url.split('/')[-2:-1][0]
                item = ArteLiveCollection([u'arte-live', u'%s' % _id], u'%s' % (a.text))
                items.append(item)
        return items

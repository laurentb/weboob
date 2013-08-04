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


import datetime
import re
import urllib
import HTMLParser

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.capabilities import NotAvailable

from .video import ArteVideo, ArteLiveVideo
from .collection import ArteLiveCollection

__all__ = ['IndexPage', 'VideoPage', 'ArteLivePage', 'ArteLiveCategorieVideoPage', 'ArteLiveVideoPage']


class ArteLiveVideoPage(BasePage):
    def get_video(self, video=None, lang='fr', quality='hd'):
        if not video:
            video = ArteVideo(self.group_dict['id'])

        urls = {}
        for url in self.document.xpath('//video')[0].getchildren():
            if url.tag.startswith('url'):
                urls[url.tag[-2:]] = url.text

        if quality in urls:
            video.url = urls[quality]
        else:
            video.url = urls.popitem()[1]
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
                    video.thumbnail = Thumbnail(parsed_element['pict'])
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
            m = re.match(r'http://liveweb.arte.tv/*', el.find('a').attrib['href'])
            if m:
                url = u'%s' % el.find('a').attrib['href']
                _id = url.split('/')[-2:-1][0]
                item = ArteLiveCollection([u'live', u'%s' % _id], u'%s' % (el.find('a').text))
                items.append(item)
        return items


class IndexPage(BasePage):
    def iter_videos(self):
        videos = self.document.getroot().cssselect("div[class=video]")
        for div in videos:
            title = div.find('h2').find('a').text
            m = re.match(r'/(fr|de|en)/videos/(.*)\.html', div.find('h2').find('a').attrib['href'])
            _id = ''
            if m:
                _id = m.group(2)
            rating = rating_max = 0
            rates = self.parser.select(div, 'div[class=rateContainer]', 1)
            for r in rates.findall('div'):
                if 'star-rating-on' in r.attrib['class']:
                    rating += 1
                rating_max += 1

            video = ArteVideo(_id)
            video.title = unicode(title)
            video.rating = rating
            video.rating_max = rating_max

            thumb = self.parser.select(div, 'img[class=thumbnail]', 1)
            video.thumbnail = Thumbnail(u'http://videos.arte.tv' + thumb.attrib['src'])

            try:
                parts = self.parser.select(div, 'div.duration_thumbnail', 1).text.split(':')
                if len(parts) == 2:
                    hours = 0
                    minutes, seconds = parts
                elif len(parts) == 3:
                    hours, minutes, seconds = parts
                else:
                    raise BrokenPageError('Unable to parse duration %r' % parts)
            except BrokenPageError:
                pass
            else:
                video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))

            video.set_empty_fields(NotAvailable, ('url',))

            yield video


class VideoPage(BasePage):
    def get_video(self, video=None, lang='fr', quality='hd'):
        if not video:
            video = ArteVideo(self.group_dict['id'])
        video.title = unicode(self.get_title())
        video.url = unicode(self.get_url(lang, quality))
        video.set_empty_fields(NotAvailable)
        return video

    def get_title(self):
        return self.document.getroot().cssselect('h1')[0].text

    def get_url(self, lang, quality):
        obj = self.parser.select(self.document.getroot(), 'object', 1)
        movie_url = self.parser.select(obj, 'param[name=movie]', 1)
        xml_url = urllib.unquote(movie_url.attrib['value'].split('videorefFileUrl=')[-1])

        doc = self.browser.get_document(self.browser.openurl(xml_url))
        videos_list = self.parser.select(doc.getroot(), 'video')
        videos = {}
        for v in videos_list:
            videos[v.attrib['lang']] = v.attrib['ref']

        if lang in videos:
            xml_url = videos[lang]
        else:
            xml_url = videos.popitem()[1]

        doc = self.browser.get_document(self.browser.openurl(xml_url))

        obj = self.parser.select(doc.getroot(), 'urls', 1)
        videos_list = self.parser.select(obj, 'url')
        urls = {}
        for v in videos_list:
            urls[v.attrib['quality']] = v.text

        if quality in urls:
            video_url = urls[quality]
        else:
            video_url = urls.popitem()[1]

        return video_url

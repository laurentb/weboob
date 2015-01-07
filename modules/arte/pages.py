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


from weboob.deprecated.browser import Page
from weboob.tools.html import html2text
from weboob.capabilities import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.capabilities.collection import Collection
from .video import ArteLiveVideo


class ArteLiveVideoPage(Page):
    def get_video(self, video=None):
        if not video:
            video = ArteLiveVideo('/%s' % self.group_dict['id'])

        div = self.document.xpath('//div[@class="bloc-presentation"]')[0]

        description = self.parser.select(div,
                                         'div[@class="field field-name-body field-type-text-with-summary field-label-hidden bloc-rte"]',
                                         1,
                                         method='xpath')
        video.description = html2text(self.parser.tostring(description))

        json_url = self.document.xpath('//div[@class="video-container"]')[0].attrib['arte_vp_url']
        return json_url, video


class ArteLivePage(Page):
    def iter_resources(self):
        items = list()
        for el in self.document.xpath('//ul[@class="filter-liste"]/li'):
            _id = el.attrib['data-target'].replace('video_box_tab_', '')
            text = self.parser.select(el, 'a/span', 1, method='xpath').text
            item = Collection([u'arte-live', u'%s' % _id], u'%s' % (text))
            items.append(item)
        return items

    def iter_videos(self, cat, lang='fr'):
        articles = self.document.xpath('//div[@id="video_box_tab_%s"]/article' % cat)
        videos = list()
        for article in articles:
            _id = article.attrib['about']
            title = self.parser.select(article,
                                   'div/div[@class="info-article "]/div/h3/a',
                                   1,
                                   method='xpath').text
            thumbnail = self.parser.select(article,
                                          'div/div/a/figure/span/span',
                                          1,
                                          method='xpath').attrib['data-src']

            video = ArteLiveVideo(_id)
            video.title = u'%s' % title
            video.thumbnail = BaseImage(thumbnail)
            video.thumbnail.url = video.thumbnail.id
            video.set_empty_fields(NotAvailable, ('url',))
            videos.append(video)
        return videos

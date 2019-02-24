# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.capabilities.collection import Collection
from weboob.capabilities.base import UserError
from weboob.capabilities import NotAvailable
from weboob.browser import PagesBrowser, URL
from weboob.tools.compat import unicode

from .pages import ArteJsonPage, GuidePage
from .video import VERSION_VIDEO, LANG, QUALITY

__all__ = ['ArteBrowser']


class ArteBrowser(PagesBrowser):
    BASEURL = 'https://www.arte.tv'
    webservice = URL(r'/guide/api/api/zones/(?P<lang>\w{2})/(?P<method_name>(videos_HOME_CREATIVE|magazines|collections|playlists|videos_subcategory|listing_MAGAZINES|listing_SEARCH|collection_videos))/\?limit=20&page=(?P<page>\d*)&(?P<pattern>.*)',
                     r'/guide/api/api/pages/(?P<_lang>\w{2})/TV_GUIDE/\?day=(?P<day>\d{4}-\d{2}-\d{2})',
                     r'https://api.arte.tv/api/player/v1/config/(?P<__lang>\w{2})/(?P<vid>.*)',
                     ArteJsonPage)

    guide = URL(r'/(?P<lang>\w{2})/guide/', GuidePage)

    def __init__(self, lang, quality, order, format, version, *args, **kwargs):
        super(ArteBrowser, self).__init__(*args, **kwargs)
        self.order = order
        self.lang = next(value for key, value in LANG.items if key == lang)
        self.version = next(value for key, value in VERSION_VIDEO.items
                            if self.lang.get('label') in value.keys() and version == key)
        self.quality = next(value for key, value in QUALITY.items if key == quality)
        self.format = format

        if self.lang.get('label') not in self.version.keys():
            raise UserError('%s is not available for %s' % (self.lang.get('label'), version))

    def search_videos(self, pattern):
        return self.webservice.go(lang=self.lang['site'],
                                  method_name='listing_SEARCH',
                                  page=1,
                                  pattern=r'query={}'.format(pattern)).iter_videos()

    def get_arte_guide_days(self, split_path):
        return self.guide.go(lang=self.lang.get('site')).iter_days(split_path=split_path)

    def get_arte_guide_videos(self, split_path):
        return self.webservice.go(_lang=self.lang.get('site'),
                                  day=split_path[-1]).iter_guide_videos()

    def get_arte_programs(self, split_path, pattern=""):
        return self.webservice.go(lang=self.lang['site'],
                                  method_name='listing_MAGAZINES',
                                  page=1,
                                  pattern=pattern).iter_programs(split_path=split_path)

    def get_arte_creative_videos(self):
        return self.webservice.go(lang=self.lang['site'],
                                  method_name='videos_HOME_CREATIVE',
                                  page=1,
                                  pattern="").iter_videos()

    def get_arte_navigation(self, split_path, collections=r'', playlists=r'', magazines=r''):
        cat = split_path[-1]

        if cat == collections or cat == playlists or cat == magazines:
            method_name, id = cat.split('_')

            return self.webservice.go(lang=self.lang['site'],
                                      method_name=method_name,
                                      page=1,
                                      pattern="id={}".format(id)).iter_programs(split_path=split_path)
        else:
            method_name = r'collection_videos' if cat.startswith('RC-') else r'videos_subcategory'

            return self.webservice.go(lang=self.lang['site'],
                                      method_name=method_name,
                                      page=1,
                                      pattern="id={}".format(cat)).iter_videos()

    def get_arte_generic_subsites(self, split_path, subsite):
        for item in subsite.values:
            yield Collection(split_path + [unicode(item.get('id'))], unicode(item.get('label')))

    def get_video(self, id, video=None):
        video = self.webservice.go(__lang=self.lang['site'], vid=id).get_video(obj=video)

        video.ext, video.url = self.get_url()
        return video

    def get_url(self):
        url, found_format = self.page.get_video_url(self.quality.get('label'), self.format,
                                                    self.version.get(self.lang.get('label')),
                                                    self.lang.get('version'))
        if found_format.startswith('HLS'):
            ext = u'm3u8'
            url = self.get_m3u8_link(url)
        else:
            ext = u'mp4'
            url = url
        return ext, url

    def get_m3u8_link(self, url):
        r = self.open(url).text.split('\n')
        baseurl = url.rpartition('/')[0]

        links_by_quality = []
        for line in r:
            if not line.startswith('#'):
                if baseurl not in line:
                    link = u'%s/%s' % (baseurl, line.replace('\n', ''))
                else:
                    link = unicode(line.replace('\n', ''))
                links_by_quality.append(link)

        if len(links_by_quality):
            try:
                return links_by_quality[self.quality.get('order')]
            except:
                return links_by_quality[0]
        return NotAvailable

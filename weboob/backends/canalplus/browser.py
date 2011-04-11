# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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

import lxml.etree

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import InitPage, CanalplusVideo, VideoPage

from weboob.capabilities.collection import Collection, CollectionNotFound

__all__ = ['CanalplusBrowser']


class XMLParser(object):
     def parse(self, data, encoding=None):
        if encoding is None:
            parser = None
        else:
            parser = lxml.etree.XMLParser(encoding=encoding, strip_cdata=False)
        return lxml.etree.XML(data.get_data(), parser)


class CanalplusBrowser(BaseBrowser):
    DOMAIN = u'service.canal-plus.com'
    ENCODING = 'utf-8'
    PAGES = {
        r'http://service.canal-plus.com/video/rest/initPlayer/cplus/': InitPage,
        r'http://service.canal-plus.com/video/rest/search/cplus/.*': VideoPage,
        r'http://service.canal-plus.com/video/rest/getVideosLiees/cplus/(?P<id>.+)': VideoPage,
        r'http://service.canal-plus.com/video/rest/getMEAs/cplus/.*': VideoPage,
        }

    #We need lxml.etree.XMLParser for read CDATA
    PARSER = XMLParser()
    FORMATS = {
        'sd': 'BAS_DEBIT',
        'hd': 'HD',
        }

    def __init__(self, quality, *args, **kwargs):
        BaseBrowser.__init__(self, parser= self.PARSER, *args, **kwargs)
        if quality in self.FORMATS:
            self.quality = self.FORMATS[quality]
        else:
            self.quality = 'HD'

    def home(self):
        self.location('http://service.canal-plus.com/video/rest/initPlayer/cplus/')

    def iter_search_results(self, pattern):
        self.location('http://service.canal-plus.com/video/rest/search/cplus/' + urllib.quote_plus(pattern))
        return self.page.iter_results()

    @id2url(CanalplusVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video, self.quality)
        
    def change_working_collection(self, splited_path):
        self.home()
        collections = self.page.collections
        
        def walk(path, collections, final=[]):
            if len(path) == 0: return final
            i = path.pop(0)
            if i in [collection.title for collection in collections if isinstance(collection, Collection)]:
                final.append(i)
            else:
                print "Error path %s unknow, %s , %s " % (i,final,[collection.title for collection in collections if isinstance(collection, Collection)] )
                raise CollectionNotFound()
                
            return walk(path, [collection.children for collection in collections if isinstance(collection, Collection) and collection.title == i][0], final)
        
        return walk(splited_path, collections)
        
    def iter_resources(self, splited_path):
        self.home()
        collections = self.page.collections
       
        def walk_res(path, collections):
            if not isinstance(collections, (list, Collection)):
                return collections
            if len(path) == 0: 
                return [collection.title for collection in collections ]
            i = path[0]
            if i not in [collection.title for collection in collections]:
                print "Error path %s unknow" % i
                raise CollectionNotFound()
                
            return walk_res(path[1:], [collection.children for collection in collections if collection.title == i][0])
        
        return walk_res(splited_path, collections)
